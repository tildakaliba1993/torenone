"""Task 4.1 — FastAPI app skeleton tests (health + structured logging).

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_app.py -q
"""

from __future__ import annotations

import json
import logging
import sys

from fastapi.testclient import TestClient
from torenone_service.app import SERVICE_NAME, SERVICE_VERSION, create_app
from torenone_service.logging_config import (
    DEFAULT_LOGGER_NAME,
    JsonFormatter,
    configure_logging,
    get_logger,
)

# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_ok(self):
        client = TestClient(create_app())
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == SERVICE_NAME
        assert body["version"] == SERVICE_VERSION

    def test_health_is_get_only(self):
        client = TestClient(create_app())
        assert client.post("/health").status_code == 405


class TestBodySizeGuard:
    def test_oversized_body_rejected_with_413(self):
        from torenone_service.app import MAX_REQUEST_BYTES

        client = TestClient(create_app())
        oversized = b"x" * (MAX_REQUEST_BYTES + 1)
        resp = client.post("/parse", content=oversized, headers={"Content-Type": "application/json"})
        assert resp.status_code == 413
        assert resp.json()["detail"] == "request body too large"

    def test_normal_body_passes_the_size_guard(self):
        # A normal-sized body is not blocked by the guard (it gets past to auth → 401/422,
        # never 413).
        client = TestClient(create_app())
        resp = client.post("/parse", json={"description": "20 m portal frame"})
        assert resp.status_code != 413


class TestSentry:
    def test_sentry_is_noop_without_dsn(self, monkeypatch):
        from torenone_service.app import _init_sentry

        monkeypatch.delenv("SENTRY_DSN", raising=False)
        assert _init_sentry() is False  # no DSN → not initialised, no error

    def test_unknown_route_404(self):
        client = TestClient(create_app())
        assert client.get("/does-not-exist").status_code == 404


# ---------------------------------------------------------------------------
# 2. App metadata
# ---------------------------------------------------------------------------


class TestAppMetadata:
    def test_title_and_version(self):
        app = create_app()
        assert app.title == SERVICE_NAME
        assert app.version == SERVICE_VERSION

    def test_openapi_served(self):
        client = TestClient(create_app())
        spec = client.get("/openapi.json").json()
        assert spec["info"]["title"] == SERVICE_NAME
        assert "/health" in spec["paths"]


# ---------------------------------------------------------------------------
# 3. JSON log formatter
# ---------------------------------------------------------------------------


class TestJsonFormatter:
    def _record(self, msg: str = "hello", level: int = logging.INFO) -> logging.LogRecord:
        return logging.LogRecord("torenone.test", level, __file__, 1, msg, None, None)

    def test_outputs_valid_json(self):
        data = json.loads(JsonFormatter().format(self._record()))
        assert data["level"] == "INFO"
        assert data["message"] == "hello"
        assert data["logger"] == "torenone.test"
        assert data["ts"].endswith("Z")

    def test_includes_extra_fields(self):
        rec = self._record("request")
        rec.method = "GET"
        rec.path = "/health"
        rec.status_code = 200
        data = json.loads(JsonFormatter().format(rec))
        assert data["method"] == "GET"
        assert data["path"] == "/health"
        assert data["status_code"] == 200

    def test_exception_info_serialised(self):
        try:
            raise ValueError("boom")
        except ValueError:
            rec = logging.LogRecord(
                "torenone.test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
            )
        data = json.loads(JsonFormatter().format(rec))
        assert "ValueError" in data["exc_info"]

    def test_one_line_per_record(self):
        out = JsonFormatter().format(self._record("line"))
        assert "\n" not in out


# ---------------------------------------------------------------------------
# 4. configure_logging
# ---------------------------------------------------------------------------


class TestConfigureLogging:
    def test_installs_single_json_handler(self):
        configure_logging()
        handlers = logging.getLogger().handlers
        assert len(handlers) == 1
        assert isinstance(handlers[0].formatter, JsonFormatter)

    def test_idempotent(self):
        configure_logging()
        configure_logging()
        assert len(logging.getLogger().handlers) == 1


# ---------------------------------------------------------------------------
# 5. Structured per-request logging middleware
# ---------------------------------------------------------------------------


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class TestRequestLogging:
    def test_request_is_logged_with_structured_fields(self):
        app = create_app()
        cap = _Capture()
        get_logger(DEFAULT_LOGGER_NAME).addHandler(cap)
        try:
            TestClient(app).get("/health")
        finally:
            get_logger(DEFAULT_LOGGER_NAME).removeHandler(cap)

        reqs = [r for r in cap.records if r.getMessage() == "request"]
        assert reqs, "expected a 'request' log line"
        last = reqs[-1]
        assert last.method == "GET"  # type: ignore[attr-defined]
        assert last.path == "/health"  # type: ignore[attr-defined]
        assert last.status_code == 200  # type: ignore[attr-defined]
        assert isinstance(last.duration_ms, float)  # type: ignore[attr-defined]

    def test_request_log_is_valid_json(self):
        """The captured request record formats to valid JSON via JsonFormatter."""
        app = create_app()
        cap = _Capture()
        get_logger(DEFAULT_LOGGER_NAME).addHandler(cap)
        try:
            TestClient(app).get("/health")
        finally:
            get_logger(DEFAULT_LOGGER_NAME).removeHandler(cap)
        rec = next(r for r in cap.records if r.getMessage() == "request")
        data = json.loads(JsonFormatter().format(rec))
        assert data["path"] == "/health"
        assert data["status_code"] == 200
