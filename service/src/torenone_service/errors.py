"""Centralised error handling (Task 4.5).

Goals:
  * **Typed errors** — known failure modes map to specific HTTP status codes with
    stable, safe messages (auth 401/503, bad input 422, upstream AI 502, report 502).
  * **Safe messages** — clients receive a short, generic reason; never a stack trace,
    an exception's internal text, or anything that could contain a secret.
  * **No secret leakage** — the OpenAI key / JWT secret never appear in a response.
    Real exception detail is logged server-side (structured) for debugging only.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from torenone_service.logging_config import get_logger

GENERIC_500_MESSAGE = "internal server error"


def install_exception_handlers(app: FastAPI) -> None:
    """Register a catch-all handler so unexpected errors never leak details."""
    logger = get_logger()

    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Full detail (incl. traceback) goes to the server log only — never the client.
        logger.error(
            "unhandled_exception",
            extra={"path": request.url.path, "error_type": type(exc).__name__},
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": GENERIC_500_MESSAGE},
        )

    app.add_exception_handler(Exception, _unhandled_exception_handler)
