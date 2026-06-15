"""Task 3.1 — server-side AI configuration for the OpenAI orchestration layer.

The AI layer (text → typed ``FrameSpec``, clarifying questions, report narrative) runs
on OpenAI ``gpt-5.5`` (with ``gpt-5.4-mini`` as a cost fallback).  This module owns the
*configuration* only — the API key and model ids — read **exclusively** from server-side
environment variables.

Security invariant (PRD NFR-6):
    The OpenAI API key NEVER leaves the server.  It is:
      * sourced only from ``OPENAI_API_KEY`` — a server-side env var, never a
        ``NEXT_PUBLIC_*`` (browser-exposed) name;
      * redacted in ``repr``/``str`` so it cannot leak into logs or tracebacks;
      * excluded (redacted) from ``safe_dict()`` — the only representation intended
        for logging, telemetry, or returning to a client.

No network calls and no ``openai`` import happen here, so this is trivially testable.
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Mapping

# Default models — overridable via env so they can be re-pinned without code changes.
DEFAULT_MODEL: str = "gpt-5.5"            # flagship: parsing + narrative (Structured Outputs)
DEFAULT_FALLBACK_MODEL: str = "gpt-5.4-mini"  # cost fallback if parsing volume grows

# Reliability defaults for the OpenAI client — a hung/slow upstream call must not block
# /parse indefinitely. Overridable via env.
DEFAULT_TIMEOUT_S: float = 30.0   # per-request timeout (seconds)
DEFAULT_MAX_RETRIES: int = 2      # bounded SDK retries on transient errors

# Environment variable names — ALL server-side only.  None are ``NEXT_PUBLIC_*``.
ENV_API_KEY: str = "OPENAI_API_KEY"
ENV_MODEL: str = "OPENAI_MODEL"
ENV_FALLBACK_MODEL: str = "OPENAI_FALLBACK_MODEL"
ENV_BASE_URL: str = "OPENAI_BASE_URL"
ENV_TIMEOUT_S: str = "OPENAI_TIMEOUT_S"
ENV_MAX_RETRIES: str = "OPENAI_MAX_RETRIES"


class MissingAPIKeyError(RuntimeError):
    """Raised when ``OPENAI_API_KEY`` is absent/blank in the server environment."""


def _positive_float(raw: str | None, default: float) -> float:
    """Parse a positive float from env; fall back to *default* on blank/invalid/non-positive."""
    try:
        value = float((raw or "").strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _non_negative_int(raw: str | None, default: int) -> int:
    """Parse a non-negative int from env; fall back to *default* on blank/invalid/negative."""
    try:
        value = int((raw or "").strip())
    except ValueError:
        return default
    return value if value >= 0 else default


def _redact(key: str) -> str:
    """Return a non-reversible hint for an API key — never the key itself.

    Shows only the last 4 characters (for ops correlation) when the key is long
    enough; otherwise a pure mask.  An empty key renders as ``<unset>``.
    """
    if not key:
        return "<unset>"
    if len(key) <= 8:
        return "***"
    return f"***{key[-4:]}"


@dataclasses.dataclass(frozen=True, repr=False)
class AIConfig:
    """Immutable server-side AI configuration.

    ``api_key`` holds the real key for server-side SDK use, but every *representation*
    of this object (repr/str/safe_dict) redacts it.
    """

    api_key: str
    model: str = DEFAULT_MODEL
    fallback_model: str = DEFAULT_FALLBACK_MODEL
    base_url: str | None = None
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = DEFAULT_MAX_RETRIES

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AIConfig:
        """Build an :class:`AIConfig` from the server environment.

        Parameters
        ----------
        env:
            Mapping to read from; defaults to ``os.environ``.  Injectable for tests.

        Raises
        ------
        MissingAPIKeyError
            If ``OPENAI_API_KEY`` is missing or blank.
        """
        source: Mapping[str, str] = os.environ if env is None else env

        api_key = (source.get(ENV_API_KEY) or "").strip()
        if not api_key:
            raise MissingAPIKeyError(
                f"{ENV_API_KEY} is not set. The OpenAI API key must be provided via the "
                "server-side environment only (never the browser / NEXT_PUBLIC_*)."
            )

        model = (source.get(ENV_MODEL) or "").strip() or DEFAULT_MODEL
        fallback_model = (source.get(ENV_FALLBACK_MODEL) or "").strip() or DEFAULT_FALLBACK_MODEL
        base_url = (source.get(ENV_BASE_URL) or "").strip() or None

        timeout_s = _positive_float(source.get(ENV_TIMEOUT_S), DEFAULT_TIMEOUT_S)
        max_retries = _non_negative_int(source.get(ENV_MAX_RETRIES), DEFAULT_MAX_RETRIES)

        return cls(
            api_key=api_key,
            model=model,
            fallback_model=fallback_model,
            base_url=base_url,
            timeout_s=timeout_s,
            max_retries=max_retries,
        )

    def __repr__(self) -> str:  # noqa: D105 — redacted on purpose
        return (
            f"AIConfig(api_key={_redact(self.api_key)!r}, model={self.model!r}, "
            f"fallback_model={self.fallback_model!r}, base_url={self.base_url!r}, "
            f"timeout_s={self.timeout_s!r}, max_retries={self.max_retries!r})"
        )

    __str__ = __repr__

    def safe_dict(self) -> dict[str, str | float | int | None]:
        """Return a dict safe to log / send anywhere — the API key is redacted.

        This is the ONLY dict representation of the config; there is deliberately no
        method that emits the raw key, so it cannot be accidentally serialised.
        """
        return {
            "model": self.model,
            "fallback_model": self.fallback_model,
            "base_url": self.base_url,
            "timeout_s": self.timeout_s,
            "max_retries": self.max_retries,
            "api_key": _redact(self.api_key),
        }
