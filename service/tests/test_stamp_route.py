"""POST /stamp — registered-engineer e-stamp route tests.

Authz branches use a fake store (no DB). The success path monkeypatches build_stamped_pdf so
it doesn't need WeasyPrint; a separate, WeasyPrint-guarded test exercises the real re-render.

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /Users/cash/TorenOne/.venv/bin/pytest service/tests/test_stamp_route.py -q
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
from torenone_kernel.report.metadata import Stamp
from torenone_kernel.report.renderer import report_fingerprint
from torenone_service import app as app_module
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig
from torenone_service.reports import RunStampContext, StampUnavailableError

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)

SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0, bay_spacing_m=6.0, number_of_bays=5
    ),
    dead=DeadLoadInputs(roof_kpa=0.20),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": "user-1", "email": "e@firm.co.za", "aud": "authenticated",
         "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def _context(*, is_engineer: bool, reg_no: str | None) -> RunStampContext:
    result = design(SPEC)
    return RunStampContext(
        firm_id="firm-1",
        engineer_name="J. Smith Pr.Eng",
        ecsa_reg_no=reg_no,
        is_registered_engineer=is_engineer,
        frame_spec=SPEC.model_dump(mode="json"),
        mode="design",
        result=result.model_dump(mode="json"),
        report_metadata=None,
        storage_path="firm-1/report-1.pdf",
    )


class _FakeStore:
    """A ReportStore that supports stamping in-memory (no DB)."""

    def __init__(self, ctx: RunStampContext | None, *, unavailable: bool = False) -> None:
        self._ctx = ctx
        self._unavailable = unavailable
        self.applied: list[dict[str, Any]] = []

    def save_report(self, **_kw: Any) -> Any:  # pragma: no cover - unused here
        raise NotImplementedError

    def load_run_for_stamp(self, *, user_id: str, run_id: str) -> RunStampContext | None:
        if self._unavailable:
            raise StampUnavailableError("no supabase store")
        return self._ctx

    def apply_stamp(
        self, *, run_id: str, firm_id: str, storage_path: str, pdf_bytes: bytes, stamp: dict[str, Any]
    ) -> None:
        self.applied.append(
            {"run_id": run_id, "firm_id": firm_id, "storage_path": storage_path,
             "pdf_bytes": pdf_bytes, "stamp": stamp}
        )


def _client(store: _FakeStore) -> TestClient:
    return TestClient(create_app(auth_config=AUTH, report_store=store))


def test_requires_auth() -> None:
    resp = TestClient(create_app(auth_config=AUTH)).post("/stamp", json={"run_id": "r1"})
    assert resp.status_code == 401


def test_run_not_found_is_404() -> None:
    resp = _client(_FakeStore(None)).post("/stamp", json={"run_id": "r1"}, headers=_headers())
    assert resp.status_code == 404


def test_non_engineer_is_forbidden() -> None:
    store = _FakeStore(_context(is_engineer=False, reg_no="ECSA 1"))
    resp = _client(store).post("/stamp", json={"run_id": "r1"}, headers=_headers())
    assert resp.status_code == 403
    assert store.applied == []


def test_engineer_without_reg_no_is_forbidden() -> None:
    store = _FakeStore(_context(is_engineer=True, reg_no=None))
    resp = _client(store).post("/stamp", json={"run_id": "r1"}, headers=_headers())
    assert resp.status_code == 403


def test_stamping_unavailable_is_503() -> None:
    store = _FakeStore(None, unavailable=True)
    resp = _client(store).post("/stamp", json={"run_id": "r1"}, headers=_headers())
    assert resp.status_code == 503


def test_successful_stamp(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _FakeStore(_context(is_engineer=True, reg_no="ECSA 20250123"))

    def _fake_build(**kwargs: Any) -> tuple[bytes, Stamp]:
        stamp = Stamp(
            engineer_name=kwargs["engineer_name"],
            ecsa_reg_no=kwargs["ecsa_reg_no"],
            stamped_at=kwargs["stamped_at"],
            fingerprint="abc123",
        )
        return b"%PDF-1.7 stamped", stamp

    monkeypatch.setattr(app_module, "build_stamped_pdf", _fake_build)
    resp = _client(store).post("/stamp", json={"run_id": "run-7"}, headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["engineer_name"] == "J. Smith Pr.Eng"
    assert body["ecsa_reg_no"] == "ECSA 20250123"
    # The stamp was recorded with the stamping user's id (audit) and bound to the PDF.
    assert len(store.applied) == 1
    rec = store.applied[0]
    assert rec["run_id"] == "run-7"
    assert rec["stamp"]["stamped_by"] == "user-1"
    assert rec["pdf_bytes"] == b"%PDF-1.7 stamped"


def _weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.skipif(not _weasyprint_available(), reason="WeasyPrint not installed")
def test_build_stamped_pdf_reproduces_fingerprint() -> None:
    """The real re-render reproduces an identical fingerprint (deterministic kernel re-run)."""
    from torenone_service.stamp_service import build_stamped_pdf

    result = design(SPEC)
    pdf, stamp = build_stamped_pdf(
        frame_spec=SPEC.model_dump(mode="json"),
        mode="design",
        result=result.model_dump(mode="json"),
        report_metadata=None,
        engineer_name="J. Smith",
        ecsa_reg_no="ECSA 1",
        stamped_at="2026-06-30T22:00:00Z",
    )
    assert pdf[:5] == b"%PDF-"
    assert stamp.fingerprint == report_fingerprint(result)
