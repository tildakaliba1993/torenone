"""Structured (JSON) logging for the engineering service (Task 4.1).

One JSON object per line on stdout — friendly to container log collectors. Any
keyword passed via the standard logging ``extra={...}`` mechanism is included as a
top-level field, so call sites can attach structured context (method, path, etc.)
without string-formatting.

No secrets are ever logged: call sites pass only non-sensitive fields, and the
service config redacts the OpenAI key (see torenone_ai.AIConfig).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

DEFAULT_LOGGER_NAME = "torenone.service"

# Attributes already present on a bare LogRecord — everything else is "extra".
_RESERVED: frozenset[str] = frozenset(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Format a LogRecord as a single JSON line, including any ``extra`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger (stdout). Idempotent."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """Return the service logger."""
    return logging.getLogger(name)
