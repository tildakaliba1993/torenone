"""FastAPI application skeleton (Task 4.1).

Provides:
  * an application factory ``create_app()`` (testable, no import-time side effects
    beyond logging configuration),
  * a ``GET /health`` liveness endpoint,
  * structured per-request logging middleware.

Auth (4.2), /parse (4.3), /design (4.4) and error handling (4.5) build on this.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAIError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse, Response
from torenone_ai import (
    DrawingDecodeError,
    FrameSpecExtraction,
    build_frame_spec,
    parse_description,
    parse_drawing,
)

from torenone_service.ai_runtime import (
    AIRuntime,
    get_ai_runtime,
    optional_ai_runtime_from_env,
)
from torenone_service.analytics import design_event_fields
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
    ParseDrawingRequest,
    ParseRequest,
    ParseResponse,
)

SERVICE_NAME = "torenone-engineering-service"
SERVICE_VERSION = "0.1.0"

# Browser origins allowed to call the service (the SPA is a different origin/port).
# Override in deployment via CORS_ALLOW_ORIGINS (comma-separated). The token is sent
# as an Authorization header (not cookies), so credentials are not allowed.
_DEFAULT_CORS_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")

# Max accepted request-body size. A FrameSpec/description payload is a few KB; 256 KB is a
# generous-but-bounded cap that blocks abusive/runaway payloads. Override via env.
MAX_REQUEST_BYTES: int = int(os.environ.get("MAX_REQUEST_BYTES", "").strip() or 256 * 1024)
# A drawing/photo payload (base64 data URL) is larger than a text description but still bounded.
MAX_IMAGE_REQUEST_BYTES: int = int(
    os.environ.get("MAX_IMAGE_REQUEST_BYTES", "").strip() or 12 * 1024 * 1024
)

# Per-IP rate limits on the expensive POST routes (abuse / runaway-cost guard). Override
# via env. /parse calls OpenAI (cost); /design runs the FEA + PDF (CPU). Defaults are
# generous for a single engineer but bound automated abuse.
PARSE_RATE_LIMIT: str = os.environ.get("PARSE_RATE_LIMIT", "").strip() or "30/minute"
DESIGN_RATE_LIMIT: str = os.environ.get("DESIGN_RATE_LIMIT", "").strip() or "30/minute"

# Per-request wall-clock budget for the CPU-bound kernel run on /design (§4.4). The kernel's
# runtime is algorithmically bounded (≤5 sizing iterations over a fixed 64-section library +
# a small FEA solve), so this is defense-in-depth against a pathological case rather than a
# hot path — normal runs land in ~15-20 s, well under the default. On exceed, /design returns
# 504. Override via env; <=0 disables.
DESIGN_TIMEOUT_S: float = float(os.environ.get("DESIGN_TIMEOUT_S", "").strip() or "120")

_T = TypeVar("_T")


class DesignTimeoutError(Exception):
    """The kernel run exceeded its per-request wall-clock budget (§4.4)."""


def _run_with_timeout(fn: Callable[[], _T], timeout_s: float) -> _T:
    """Run *fn* on a worker thread, returning its result or raising on timeout/error.

    A non-positive ``timeout_s`` runs *fn* inline (no guard). On timeout a
    :class:`DesignTimeoutError` is raised; the worker thread is a daemon and is left to
    finish in the background (a sync CPU-bound Python call cannot be force-cancelled) —
    acceptable because the kernel's runtime is bounded, so this only bounds the *client's*
    wait. Any exception raised by *fn* is re-raised to the caller unchanged.
    """
    if timeout_s <= 0:
        return fn()

    box: dict[str, object] = {}

    def _target() -> None:
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001 — re-raised on the calling thread
            box["error"] = exc

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join(timeout_s)
    if worker.is_alive():
        raise DesignTimeoutError(f"design exceeded {timeout_s:.0f}s")
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box["value"]  # type: ignore[return-value]


def _init_sentry() -> bool:
    """Initialise Sentry error tracking iff ``SENTRY_DSN`` is set. No-op otherwise.

    Returns True if Sentry was initialised. Safe to call when sentry-sdk isn't configured —
    nothing is sent and no key is required for local/dev/tests.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production").strip() or "production",
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0").strip() or 0.0),
        send_default_pii=False,  # never ship user PII / request bodies
    )
    return True


def _cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return list(_DEFAULT_CORS_ORIGINS)


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
    design_timeout_s: float | None = None,
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
    design_timeout_s:
        Per-request wall-clock budget for the CPU-bound kernel run on /design (§4.4).
        Defaults to ``DESIGN_TIMEOUT_S`` (120 s); ``<= 0`` disables the guard.
    """
    design_timeout = DESIGN_TIMEOUT_S if design_timeout_s is None else design_timeout_s
    configure_logging()
    logger = get_logger()
    _init_sentry()

    app = FastAPI(
        title=SERVICE_NAME,
        version=SERVICE_VERSION,
        summary="TorenOne engineering service — AI orchestration + kernel + report.",
    )
    # Per-app rate limiter (keyed on client IP). Created per app instance so test apps don't
    # share counter state. Routes opt in via @limiter.limit (see /parse, /design).
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    # slowapi's handler is typed (Request, RateLimitExceeded); Starlette expects
    # (Request, Exception). The mismatch is a known slowapi typing quirk — safe to ignore.
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def limit_body_size(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Reject over-large request bodies early (abuse / runaway-cost guard).

        A FrameSpec / description payload is small (a few KB); the cap is generous but
        bounded. Enforced via the Content-Length header (clients must send it).
        """
        # The drawings-in endpoint carries an image, so it gets a larger (still bounded) cap.
        limit = (
            MAX_IMAGE_REQUEST_BYTES
            if request.url.path == "/parse-drawing"
            else MAX_REQUEST_BYTES
        )
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > limit:
                    return JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content={"detail": "request body too large"},
                    )
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "invalid Content-Length"},
                )
        return await call_next(request)

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
    @limiter.limit(PARSE_RATE_LIMIT)
    def parse(
        request: Request,
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

    @app.post("/parse-drawing")
    @limiter.limit(PARSE_RATE_LIMIT)
    def parse_drawing_route(
        request: Request,
        body: ParseDrawingRequest,
        user: AuthenticatedUser = Depends(require_user),
        ai: AIRuntime = Depends(get_ai_runtime),
    ) -> ParseResponse:
        """Parse a frame DRAWING/sketch into a FrameSpec (or questions / refusal).

        The drawings-in front door. Same protection, rate limit, and response shape as
        ``/parse`` — and the same safety contract: the vision model only transcribes the
        labelled dimensions into the nullable extraction; no engineering number is produced,
        and every value flows through the existing confirm gate (see torenone_ai.parse_drawing).
        """
        try:
            result = parse_drawing(
                body.image_data_url, client=ai.client, model=ai.model, note=body.note
            )
        except DrawingDecodeError as exc:
            # Malformed / unreadable image or PDF — a bad-input error, not an outage.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="couldn't read that file — please upload a clear image or a valid PDF",
            ) from exc
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
            "parse_drawing",
            extra={"user_id": user.user_id, "status": response.status},
        )
        return response

    @app.post("/build-spec")
    @limiter.limit(PARSE_RATE_LIMIT)
    def build_spec_route(
        request: Request,
        body: FrameSpecExtraction,
        user: AuthenticatedUser = Depends(require_user),
    ) -> ParseResponse:
        """Build a FrameSpec from the merged read + clarified values — the clarify-loop commit.

        Deterministic: **no LLM runs here.** ``build_frame_spec`` only flags missing required
        fields, applies documented defaults, and validates — so the engineer's answers combine with
        whatever was already read (from a brief or a drawing) into a spec, with no new chance for the
        model to misread. Protected; no AI runtime needed.
        """
        response = ParseResponse.from_result(build_frame_spec(body))
        logger.info(
            "build_spec",
            extra={"user_id": user.user_id, "status": response.status},
        )
        return response

    @app.post("/design")
    @limiter.limit(DESIGN_RATE_LIMIT)
    def design(
        request: Request,
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
        started = time.perf_counter()
        try:
            # Bound the CPU-bound kernel run with a per-request wall-clock budget (§4.4).
            result = _run_with_timeout(lambda: run_design(body), design_timeout)
        except DesignTimeoutError as exc:
            logger.warning(
                "design_timeout",
                extra={"user_id": user.user_id, "mode": body.mode, "timeout_s": design_timeout},
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="the design run took too long and was aborted",
            ) from exc
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
        # Minimal product-analytics signal (Task 5.4): one structured event per design
        # run — pass/fail, governing utilisation, tonnage, latency. No PII.
        duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
        logger.info(
            "design",
            extra=design_event_fields(
                user_id=user.user_id,
                mode=body.mode,
                result=result,
                duration_ms=duration_ms,
                report_id=stored.report_id,
            ),
        )
        return DesignResponse(result=result, report=stored)

    logger.info(
        "service_startup",
        extra={"service": SERVICE_NAME, "version": SERVICE_VERSION},
    )
    return app
