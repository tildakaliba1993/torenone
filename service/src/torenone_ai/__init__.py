"""TorenOne AI orchestration layer (Phase 3).

Server-side only.  Turns natural-language descriptions into a typed ``FrameSpec``,
asks clarifying questions, and drafts report narrative — using OpenAI ``gpt-5.5``.
The LLM never computes engineering numbers; the kernel does all arithmetic.
"""

from torenone_ai.client import build_client, build_client_from_env
from torenone_ai.config import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_MODEL,
    AIConfig,
    MissingAPIKeyError,
)

__all__ = [
    "AIConfig",
    "MissingAPIKeyError",
    "DEFAULT_MODEL",
    "DEFAULT_FALLBACK_MODEL",
    "build_client",
    "build_client_from_env",
]
