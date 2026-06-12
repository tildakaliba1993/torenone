"""Task 4.4 — POST /design route tests.

The kernel runs for real (deterministic, CI-safe). The PDF builder and the report
store are injected fakes, so no WeasyPrint / Supabase is needed.

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_design_route.py -q
"""

from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
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
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig
from torenone_service.reports import InMemoryReportStore
from torenone_service.schemas import StoredReport


def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401

        return True
    except Exception:
        return False

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)
FAKE_PDF = b"%PDF-1.7 fake calc package"


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": "user-9", "email": "e@firm.co.za", "aud": "authenticated",
         "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
        bay_spacing_m=6.0, number_of_bays=5,
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)


class _FakeReportBuilder:
    def __init__(self) -> None:
        self.calls: list[DesignResult] = []

    def build_pdf(self, result: DesignResult) -> bytes:
        self.calls.append(result)
        return FAKE_PDF


class _RecordingStore:
    def __init__(self) -> None:
        self.saved: list[dict[str, Any]] = []

    def save_report(
        self, *, user_id: str, project_id: str | None,
        result: DesignResult, pdf_bytes: bytes, mode: str = "design",
    ) -> StoredReport:
        self.saved.append(
            {"user_id": user_id, "project_id": project_id, "pdf_bytes": pdf_bytes, "mode": mode}
        )
        return StoredReport(
            run_id="run-123", report_id="rep-123",
            storage_path=f"reports/{user_id}/run-123.pdf", size_bytes=len(pdf_bytes),
        )


def _client(
    builder: _FakeReportBuilder | None = None,
    store: _RecordingStore | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            auth_config=AUTH,
            report_builder=builder or _FakeReportBuilder(),
            report_store=store or _RecordingStore(),
        )
    )


def _body(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"spec": SPEC.model_dump(mode="json"), "mode": "design"}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Design mode — happy path
# ---------------------------------------------------------------------------


class TestDesignMode:
    def test_design_returns_result_and_report(self):
        resp = _client().post("/design", json=_body(), headers=_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["sections"]  # kernel chose sections
        assert "checks" in body["result"]
        assert body["report"]["run_id"] == "run-123"
        assert body["report"]["size_bytes"] == len(FAKE_PDF)

    def test_result_matches_kernel(self):
        body = _client().post("/design", json=_body(), headers=_headers()).json()
        expected = design(SPEC)
        assert body["result"]["passed"] == expected.passed
        got = {s["member"]: s["designation"] for s in body["result"]["sections"]}
        want = {s.member: s.designation for s in expected.sections}
        assert got == want

    def test_builder_and_store_called(self):
        builder, store = _FakeReportBuilder(), _RecordingStore()
        _client(builder, store).post("/design", json=_body(project_id="proj-1"),
                                     headers=_headers())
        assert len(builder.calls) == 1
        assert len(store.saved) == 1
        assert store.saved[0]["user_id"] == "user-9"
        assert store.saved[0]["project_id"] == "proj-1"
        assert store.saved[0]["pdf_bytes"] == FAKE_PDF

    def test_custom_cost_rate_applied(self):
        body = _client().post(
            "/design", json=_body(cost_rate_zar_per_kg=50.0), headers=_headers()
        ).json()
        expected = design(SPEC, 50.0)
        assert body["result"]["indicative_cost_zar"] == pytest.approx(
            expected.indicative_cost_zar
        )


# ---------------------------------------------------------------------------
# 2. Check mode (PRD FR-24)
# ---------------------------------------------------------------------------


class TestCheckMode:
    def test_check_with_valid_sections(self):
        sections = [s.model_dump() for s in design(SPEC).sections]
        resp = _client().post(
            "/design", json=_body(mode="check", sections=sections), headers=_headers()
        )
        assert resp.status_code == 200
        assert resp.json()["result"]["sections"]

    def test_check_without_sections_422(self):
        resp = _client().post("/design", json=_body(mode="check"), headers=_headers())
        assert resp.status_code == 422

    def test_check_unknown_designation_422(self):
        sections = [
            {"member": "rafter", "designation": "NOT-A-REAL-SECTION"},
            {"member": "column", "designation": "NOT-A-REAL-SECTION"},
        ]
        resp = _client().post(
            "/design", json=_body(mode="check", sections=sections), headers=_headers()
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 3. Auth + validation guards
# ---------------------------------------------------------------------------


class TestGuards:
    def test_requires_auth(self):
        resp = _client().post("/design", json=_body())
        assert resp.status_code == 401

    def test_invalid_spec_422(self):
        bad = SPEC.model_dump(mode="json")
        bad["geometry"]["roof_pitch_deg"] = 80.0  # > 45 -> kernel model rejects
        resp = _client().post("/design", json={"spec": bad}, headers=_headers())
        assert resp.status_code == 422

    def test_missing_spec_422(self):
        resp = _client().post("/design", json={"mode": "design"}, headers=_headers())
        assert resp.status_code == 422

    def test_bad_mode_422(self):
        resp = _client().post("/design", json=_body(mode="bogus"), headers=_headers())
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 4. End-to-end with the REAL report builder (Python 3.11 + WeasyPrint only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _weasyprint_available(), reason="WeasyPrint not installed")
class TestRealPdf:
    def test_design_with_default_builder_produces_pdf(self):
        store = InMemoryReportStore()
        # No report_builder injected -> default WeasyPrintReportBuilder is used.
        client = TestClient(create_app(auth_config=AUTH, report_store=store))
        resp = client.post("/design", json=_body(), headers=_headers())
        assert resp.status_code == 200
        report_id = resp.json()["report"]["report_id"]
        pdf = store.reports[report_id]
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 10_000
