"""AI runtime wiring for the service (Task 4.3).

Bundles the server-side OpenAI client + model id and exposes them to routes via a
FastAPI dependency. The runtime is built once from :class:`~torenone_ai.AIConfig`
and stored on ``app.state`` (or injected in tests), so the OpenAI key is read from
the environment exactly once and never reaches a route handler directly.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import HTTPException, Request, status
from torenone_ai import AIConfig, MissingAPIKeyError, build_client

from torenone_service.logging_config import get_logger


@dataclasses.dataclass(frozen=True)
class AIRuntime:
    """An OpenAI client plus the model id to call it with."""

    client: Any
    model: str


def optional_ai_runtime_from_env() -> AIRuntime | None:
    """Build an :class:`AIRuntime` from env, or None (warning) if no key is set.

    The app still starts without a key so liveness works; AI-backed routes then
    return 503 until ``OPENAI_API_KEY`` is provided.
    """
    try:
        config = AIConfig.from_env()
    except MissingAPIKeyError:
        get_logger().warning(
            "ai_not_configured",
            extra={"reason": "OPENAI_API_KEY not set; AI routes return 503"},
        )
        return None
    return AIRuntime(client=build_client(config), model=config.model)


def get_ai_runtime(request: Request) -> AIRuntime:
    """FastAPI dependency: the configured AI runtime, or 503 if unconfigured."""
    runtime: AIRuntime | None = getattr(request.app.state, "ai_runtime", None)
    if runtime is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured",
        )
    return runtime
