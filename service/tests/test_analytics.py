"""Task 5.4 — product-analytics event signal tests.

The design event is built deterministically from a real kernel result and emitted as a
structured log line by the /design route. The kernel runs for real (CI-safe); the PDF
builder + store are injected fakes (see test_design_route).
"""

from __future__ import annotations

import logging
import time

import jwt
from fastapi.testclient import TestClient
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import DesignResult
from torenone_service.analytics import DESIGN_EVENT, design_event_fields
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig
from torenone_service.schemas import StoredReport

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)
FAKE_PDF = b"%PDF-1.7 fake calc package"

SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
        bay_spacing_m=6.0, number_of_bays=5,
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": "user-9", "email": "e@firm.co.za", "aud": "authenticated",
         "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


class _FakeReportBuilder:
    def build_pdf(self, result: DesignResult) -> bytes:
        return FAKE_PDF


class _FakeStore:
    def save_report(
        self, *, user_id: str, project_id: str | None,
        result: DesignResult, pdf_bytes: bytes, mode: str = "design",
    ) -> StoredReport:
        return StoredReport(
            run_id="run-1", report_id="rep-1",
            storage_path=f"reports/{user_id}/run-1.pdf", size_bytes=len(pdf_bytes),
        )


def _client() -> TestClient:
    return TestClient(
        create_app(auth_config=AUTH, report_builder=_FakeReportBuilder(), report_store=_FakeStore())
    )


# ---------------------------------------------------------------------------
# 1. The event-fields helper
# ---------------------------------------------------------------------------


class TestDesignEventFields:
    def test_captures_the_5_4_signal(self):
        result = design(SPEC)
        fields = design_event_fields(
            user_id="user-9", mode="design", result=result,
            duration_ms=123.45, report_id="rep-1",
        )
        assert fields["event"] == DESIGN_EVENT
        assert fields["user_id"] == "user-9"
        assert fields["mode"] == "design"
        assert fields["passed"] == result.passed
        assert fields["governing_utilisation"] == result.governing_utilisation
        assert fields["total_steel_tonnes"] == result.total_steel_tonnes
        assert fields["section_count"] == len(result.sections)
        assert fields["duration_ms"] == 123.45
        assert fields["report_id"] == "rep-1"

    def test_no_pii(self):
        # Only the opaque user_id is included — never email/description/frame_spec.
        result = design(SPEC)
        fields = design_event_fields(
            user_id="user-9", mode="design", result=result, duration_ms=1.0
        )
        assert "email" not in fields
        assert "frame_spec" not in fields
        assert "description" not in fields


# ---------------------------------------------------------------------------
# 2. The route emits the event
# ---------------------------------------------------------------------------


class TestRouteEmitsEvent:
    def test_design_route_logs_analytics_event(self):
        # create_app() calls configure_logging(), which clears root handlers — so we
        # attach our own capturing handler to the service logger *after* building the
        # client, then drive a real design.
        client = _client()
        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = _Capture()
        logger = logging.getLogger("torenone.service")
        logger.addHandler(handler)
        try:
            resp = client.post(
                "/design",
                json={"spec": SPEC.model_dump(mode="json"), "mode": "design"},
                headers=_headers(),
            )
        finally:
            logger.removeHandler(handler)

        assert resp.status_code == 200
        events = [r for r in records if getattr(r, "event", None) == DESIGN_EVENT]
        assert len(events) == 1
        record = events[0]
        assert record.user_id == "user-9"  # type: ignore[attr-defined]
        assert record.mode == "design"  # type: ignore[attr-defined]
        assert isinstance(record.duration_ms, float)  # type: ignore[attr-defined]
        assert record.passed == resp.json()["result"]["passed"]  # type: ignore[attr-defined]
