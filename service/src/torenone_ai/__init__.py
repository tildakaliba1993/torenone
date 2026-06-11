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
from torenone_ai.parsing import (
    Assumption,
    FrameSpecExtraction,
    MissingField,
    ParseResult,
    build_frame_spec,
    parse_description,
    parse_description_from_env,
)

__all__ = [
    "AIConfig",
    "MissingAPIKeyError",
    "DEFAULT_MODEL",
    "DEFAULT_FALLBACK_MODEL",
    "build_client",
    "build_client_from_env",
    # Spec parsing (Task 3.2)
    "FrameSpecExtraction",
    "ParseResult",
    "MissingField",
    "Assumption",
    "build_frame_spec",
    "parse_description",
    "parse_description_from_env",
]
