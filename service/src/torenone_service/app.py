"""FastAPI application skeleton (Task 4.1).

Provides:
  * an application factory ``create_app()`` (testable, no import-time side effects
    beyond logging configuration),
  * a ``GET /health`` liveness endpoint,
  * structured per-request logging middleware.

Auth (4.2), /parse (4.3), /design (4.4) and error handling (4.5) build on this.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, Request, status
from openai import OpenAIError
from starlette.responses import Response
from torenone_ai import parse_description

from torenone_service.ai_runtime import (
    AIRuntime,
    get_ai_runtime,
    optional_ai_runtime_from_env,
)
from torenone_service.auth import (
    AuthConfig,
    AuthenticatedUser,
    MissingJWTSecretError,
    require_user,
)
from torenone_service.design_service import DesignError, run_design
from torenone_service.errors import install_exception_handlers
from torenone_service.logging_config import configure_logging, get_logger
from torenone_service.reports import (
    ReportBuilder,
    ReportStore,
    WeasyPrintReportBuilder,
    default_report_store,
    get_report_builder,
    get_report_store,
)
from torenone_service.schemas import (
    DesignRequest,
    DesignResponse,
    ParseRequest,
    ParseResponse,
)

SERVICE_NAME = "torenone-engineering-service"
SERVICE_VERSION = "0.1.0"


def _optional_auth_config_from_env() -> AuthConfig | None:
    """Load AuthConfig from env, or None (logging a warning) if the secret is unset.

    The app still starts unconfigured so liveness checks work; protected routes then
    return 503 until the secret is provided.
    """
    try:
        return AuthConfig.from_env()
    except MissingJWTSecretError:
        get_logger().warning(
            "auth_not_configured",
            extra={"reason": "SUPABASE_JWT_SECRET not set; protected routes return 503"},
        )
        return None


def create_app(
    *,
    auth_config: AuthConfig | None = None,
    ai_runtime: AIRuntime | None = None,
    report_builder: ReportBuilder | None = None,
    report_store: ReportStore | None = None,
) -> FastAPI:
    """Build and return the FastAPI application.

    Parameters
    ----------
    auth_config:
        Injected JWT verification config (tests). If omitted, it is loaded from the
        environment (``SUPABASE_JWT_SECRET``); if that is absent, protected routes 503.
    ai_runtime:
        Injected OpenAI client + model (tests). If omitted, it is built from the
        environment (``OPENAI_API_KEY``); if that is absent, AI routes 503.
    report_builder / report_store:
        Injected report PDF builder + persistence (tests). Default to WeasyPrint +
        an in-process store; a Supabase-backed store is wired in Phase 5.
    """
    configure_logging()
    logger = get_logger()

    app = FastAPI(
        title=SERVICE_NAME,
        version=SERVICE_VERSION,
        summary="TorenOne engineering service — AI orchestration + kernel + report.",
    )
    app.state.auth_config = (
        auth_config if auth_config is not None else _optional_auth_config_from_env()
    )
    app.state.ai_runtime = (
        ai_runtime if ai_runtime is not None else optional_ai_runtime_from_env()
    )
    app.state.report_builder = (
        report_builder if report_builder is not None else WeasyPrintReportBuilder()
    )
    app.state.report_store = (
        report_store if report_store is not None else default_report_store()
    )
    install_exception_handlers(app)

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe — no external dependencies are checked (public)."""
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
        }

    @app.get("/me")
    async def me(user: AuthenticatedUser = Depends(require_user)) -> AuthenticatedUser:
        """Return the authenticated caller — protected (requires a valid Supabase JWT)."""
        return user

    @app.post("/parse")
    def parse(
        body: ParseRequest,
        user: AuthenticatedUser = Depends(require_user),
        ai: AIRuntime = Depends(get_ai_runtime),
    ) -> ParseResponse:
        """Parse a free-text description into a FrameSpec (or questions / refusal).

        Protected. Runs as a sync route so the blocking OpenAI call is off the event
        loop. No engineering numbers are produced by the model (see torenone_ai).
        """
        try:
            result = parse_description(body.description, client=ai.client, model=ai.model)
        except OpenAIError as exc:
            logger.warning(
                "ai_upstream_error",
                extra={"user_id": user.user_id, "error_type": type(exc).__name__},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="the AI parsing service is temporarily unavailable",
            ) from exc
        response = ParseResponse.from_result(result)
        logger.info(
            "parse",
            extra={"user_id": user.user_id, "status": response.status},
        )
        return response

    @app.post("/design")
    def design(
        body: DesignRequest,
        user: AuthenticatedUser = Depends(require_user),
        builder: ReportBuilder = Depends(get_report_builder),
        store: ReportStore = Depends(get_report_store),
    ) -> DesignResponse:
        """Run the kernel on a confirmed FrameSpec, build + store the PDF, return it.

        Protected. ``mode=design`` auto-sizes; ``mode=check`` verifies supplied
        sections (PRD FR-24). Input-driven kernel failures become 422; a failed
        *check* (passed=False) is a normal 200 result.
        """
        try:
            result = run_design(body)
        except DesignError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=exc.message
            ) from exc

        try:
            pdf_bytes = builder.build_pdf(result)
            stored = store.save_report(
                user_id=user.user_id,
                project_id=body.project_id,
                result=result,
                pdf_bytes=pdf_bytes,
                mode=body.mode,
            )
        except Exception as exc:
            logger.error(
                "report_failed",
                extra={"user_id": user.user_id, "mode": body.mode},
                exc_info=exc,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="failed to generate or store the report",
            ) from exc
        logger.info(
            "design",
            extra={
                "user_id": user.user_id,
                "mode": body.mode,
                "passed": result.passed,
                "report_id": stored.report_id,
            },
        )
        return DesignResponse(result=result, report=stored)

    logger.info(
        "service_startup",
        extra={"service": SERVICE_NAME, "version": SERVICE_VERSION},
    )
    return app
