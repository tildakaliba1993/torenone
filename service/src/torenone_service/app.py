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

from fastapi import Depends, FastAPI, Request
from starlette.responses import Response

from torenone_service.auth import (
    AuthConfig,
    AuthenticatedUser,
    MissingJWTSecretError,
    require_user,
)
from torenone_service.logging_config import configure_logging, get_logger

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


def create_app(*, auth_config: AuthConfig | None = None) -> FastAPI:
    """Build and return the FastAPI application.

    Parameters
    ----------
    auth_config:
        Injected JWT verification config (tests). If omitted, it is loaded from the
        environment (``SUPABASE_JWT_SECRET``); if that is absent, protected routes 503.
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

    logger.info(
        "service_startup",
        extra={"service": SERVICE_NAME, "version": SERVICE_VERSION},
    )
    return app
