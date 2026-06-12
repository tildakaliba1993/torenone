"""Tests for the Supabase-backed ReportStore (Task 5.6).

Three layers, none needing a live Supabase project:
  * the Storage uploader's HTTP request is asserted with an httpx mock transport,
  * the store rejects a missing project_id without touching the DB,
  * the full persistence path is exercised against a real Postgres (the same harness
    + migrations + seed used by the Phase 5 RLS tests), with a fake uploader — proving
    the runs + reports rows are written firm-scoped with the right storage path.

The DB test skips cleanly without DATABASE_URL; CI provides Postgres so it runs there.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_service.reports import SupabaseReportStore, SupabaseStorageUploader

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SUPABASE = _REPO_ROOT / "supabase"
_HARNESS = _SUPABASE / "tests" / "harness" / "00_supabase_stubs.sql"
_MIGRATIONS = sorted((_SUPABASE / "migrations").glob("*.sql"))
_SEED = _SUPABASE / "seed.sql"
_DB_URL = os.environ.get("DATABASE_URL") or os.environ.get("TORENONE_TEST_DATABASE_URL")

DEV_USER = "11111111-1111-1111-1111-111111111111"
DEV_PROJECT = "22222222-2222-2222-2222-222222222222"

SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
        bay_spacing_m=6.0, number_of_bays=5,
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)


class _FakeUploader:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def upload(self, *, bucket: str, path: str, data: bytes, content_type: str) -> None:
        self.calls.append({"bucket": bucket, "path": path, "data": data, "content_type": content_type})


# --------------------------------------------------------------------------- #
# Storage uploader — HTTP contract (no DB, no live Supabase)
# --------------------------------------------------------------------------- #
def test_storage_uploader_posts_to_supabase_storage_api() -> None:
    httpx = pytest.importorskip("httpx")
    captured: dict[str, Any] = {}

    def handler(request: Any) -> Any:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["apikey"] = request.headers.get("apikey")
        captured["content_type"] = request.headers.get("content-type")
        captured["body"] = request.content
        return httpx.Response(200, json={"Key": "reports/x"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    uploader = SupabaseStorageUploader(
        base_url="https://proj.supabase.co/", service_role_key="svc-key", client=client
    )

    uploader.upload(bucket="reports", path="firm-1/abc.pdf", data=b"%PDF-data", content_type="application/pdf")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://proj.supabase.co/storage/v1/object/reports/firm-1/abc.pdf"
    assert captured["authorization"] == "Bearer svc-key"
    assert captured["apikey"] == "svc-key"
    assert captured["content_type"] == "application/pdf"
    assert captured["body"] == b"%PDF-data"


def test_storage_uploader_raises_on_http_error() -> None:
    httpx = pytest.importorskip("httpx")
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(403)))
    uploader = SupabaseStorageUploader(base_url="https://p.supabase.co", service_role_key="k", client=client)
    with pytest.raises(httpx.HTTPStatusError):
        uploader.upload(bucket="reports", path="f/x.pdf", data=b"x", content_type="application/pdf")


# --------------------------------------------------------------------------- #
# Store guard — never persists without a project (no DB touched)
# --------------------------------------------------------------------------- #
def test_store_requires_project_id() -> None:
    def _boom() -> Any:
        raise AssertionError("must not open a DB connection when project_id is missing")

    store = SupabaseReportStore(connect=_boom, uploader=_FakeUploader())
    with pytest.raises(ValueError, match="project_id"):
        store.save_report(user_id=DEV_USER, project_id=None, result=design(SPEC), pdf_bytes=b"x")


# --------------------------------------------------------------------------- #
# Full persistence path — real Postgres (skipped without DATABASE_URL)
# --------------------------------------------------------------------------- #
psycopg = pytest.importorskip("psycopg")
_db = pytest.mark.skipif(not _DB_URL, reason="no DATABASE_URL — Supabase store DB test needs a Postgres")


@pytest.fixture(scope="module")
def seeded_db_url() -> str:
    try:
        conn = psycopg.connect(_DB_URL, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"cannot connect to DATABASE_URL: {exc}")
    with conn, conn.cursor() as cur:
        cur.execute("drop schema if exists public cascade; create schema public;")
        cur.execute("drop schema if exists auth cascade;")
        cur.execute("drop schema if exists storage cascade;")
        cur.execute(_HARNESS.read_text())
        for migration in _MIGRATIONS:
            cur.execute(migration.read_text())
        cur.execute(_SEED.read_text())
    conn.close()
    return _DB_URL  # type: ignore[return-value]


@_db
def test_supabase_store_persists_run_and_report(seeded_db_url: str) -> None:
    uploader = _FakeUploader()
    store = SupabaseReportStore(connect=lambda: psycopg.connect(seeded_db_url), uploader=uploader)
    result = design(SPEC)

    stored = store.save_report(
        user_id=DEV_USER, project_id=DEV_PROJECT, result=result, pdf_bytes=b"%PDF-calc", mode="check"
    )

    # The PDF was uploaded under <firm_id>/<report_id>.pdf into the reports bucket.
    assert len(uploader.calls) == 1
    call = uploader.calls[0]
    assert call["bucket"] == "reports"
    assert call["data"] == b"%PDF-calc"
    assert call["content_type"] == "application/pdf"
    assert call["path"] == stored.storage_path

    with psycopg.connect(seeded_db_url) as conn, conn.cursor() as cur:
        firm_id = cur.execute("select firm_id from public.profiles where id = %s", (DEV_USER,)).fetchone()[0]
        run = cur.execute(
            "select project_id, firm_id, mode, status, passed, created_by from public.runs where id = %s",
            (stored.run_id,),
        ).fetchone()
        report = cur.execute(
            "select run_id, firm_id, storage_path from public.reports where id = %s",
            (stored.report_id,),
        ).fetchone()

    assert run is not None, "the runs row was not written"
    assert str(run[0]) == DEV_PROJECT          # project_id
    assert str(run[1]) == str(firm_id)         # firm_id resolved from the profile
    assert run[2] == "check"                   # mode threaded through
    assert run[3] == "complete"                # status
    assert isinstance(run[4], bool)            # passed (from the kernel result)
    assert str(run[5]) == DEV_USER             # created_by

    assert report is not None, "the reports row was not written"
    assert str(report[0]) == stored.run_id
    assert str(report[1]) == str(firm_id)
    assert report[2] == stored.storage_path
    assert stored.storage_path == f"{firm_id}/{stored.report_id}.pdf"
    assert stored.size_bytes == len(b"%PDF-calc")
