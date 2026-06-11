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

from fastapi import FastAPI, Request
from starlette.responses import Response

from torenone_service.logging_config import configure_logging, get_logger

SERVICE_NAME = "torenone-engineering-service"
SERVICE_VERSION = "0.1.0"


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    configure_logging()
    logger = get_logger()

    app = FastAPI(
        title=SERVICE_NAME,
        version=SERVICE_VERSION,
        summary="TorenOne engineering service — AI orchestration + kernel + report.",
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
        """Liveness probe — no external dependencies are checked."""
        return {
            "status": "ok",
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
        }

    logger.info(
        "service_startup",
        extra={"service": SERVICE_NAME, "version": SERVICE_VERSION},
    )
    return app
