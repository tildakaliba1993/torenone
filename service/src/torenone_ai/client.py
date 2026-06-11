"""Task 3.1 — server-side OpenAI client factory.

A thin wrapper that turns an :class:`~torenone_ai.config.AIConfig` into a configured
``openai.OpenAI`` client.  The ``openai`` SDK is imported lazily so that configuration
and key-exposure guard tests run without requiring the package or a live key.

The client is constructed server-side only; the API key never reaches the browser.
"""

from __future__ import annotations

from typing import Any

from torenone_ai.config import AIConfig


def build_client(config: AIConfig) -> Any:
    """Construct a server-side OpenAI client from *config*.

    Parameters
    ----------
    config:
        Validated :class:`AIConfig` (key + optional base_url).

    Returns
    -------
    openai.OpenAI
        A configured client.  Typed as ``Any`` to avoid importing the SDK at module
        load (keeps the config layer importable without ``openai`` installed).

    Raises
    ------
    ImportError
        If the ``openai`` package is not installed.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - exercised only without the SDK
        raise ImportError(
            "The 'openai' package is required to build the OpenAI client. "
            "Install it in the engineering-service environment: pip install openai"
        ) from exc

    kwargs: dict[str, Any] = {"api_key": config.api_key}
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs)


def build_client_from_env(env: dict | None = None) -> Any:
    """Convenience: read :class:`AIConfig` from the environment and build a client."""
    return build_client(AIConfig.from_env(env))
