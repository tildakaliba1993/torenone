"""§6.2 — report-PDF retention pruner tests.

The DB connection and the Storage remover are injected, so the pruning logic is tested
with no live Supabase project. The HTTP remover's request contract is asserted via an
httpx MockTransport (mirroring test_reports_supabase.py).

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest \
        service/tests/test_prune_reports.py -q
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import httpx
import pytest
from prune_reports import (
    BUCKET,
    ExpiredReport,
    SupabaseStorageRemover,
    main,
    prune_reports,
)


class _FakeCursor:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _FakeCursor:
        self._conn.calls.append(("execute", sql, params))
        return self

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._conn.rows


class _FakeConn:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows
        self.calls: list[tuple[Any, ...]] = []

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self)

    def commit(self) -> None:
        self.calls.append(("commit",))

    def close(self) -> None:
        self.calls.append(("close",))


class _RecordingRemover:
    def __init__(self) -> None:
        self.removed: list[tuple[str, str]] = []

    def remove(self, *, bucket: str, path: str) -> None:
        self.removed.append((bucket, path))


ROWS = [
    ("rep-old-1", "firm-a/rep-old-1.pdf"),
    ("rep-old-2", "firm-a/rep-old-2.pdf"),
]


# ---------------------------------------------------------------------------
# 1. Dry-run vs apply
# ---------------------------------------------------------------------------


class TestPrune:
    def test_dry_run_lists_without_deleting(self):
        conn, remover = _FakeConn(list(ROWS)), _RecordingRemover()
        acted = prune_reports(conn=conn, remover=remover, retention_days=365, apply=False)
        assert [r.report_id for r in acted] == ["rep-old-1", "rep-old-2"]
        # No Storage deletion, no DELETE/commit in dry-run.
        assert remover.removed == []
        assert not any(c[0] == "commit" for c in conn.calls)
        assert not any("delete" in str(c[1]).lower() for c in conn.calls if c[0] == "execute")

    def test_apply_deletes_storage_before_row(self):
        conn, remover = _FakeConn(list(ROWS)), _RecordingRemover()
        acted = prune_reports(conn=conn, remover=remover, retention_days=365, apply=True)
        assert len(acted) == 2
        # Every expired object removed from Storage.
        assert remover.removed == [
            (BUCKET, "firm-a/rep-old-1.pdf"),
            (BUCKET, "firm-a/rep-old-2.pdf"),
        ]
        # And every row deleted + committed.
        deletes = [c for c in conn.calls if c[0] == "execute" and "delete" in c[1].lower()]
        assert len(deletes) == 2
        assert deletes[0][2] == ("rep-old-1",)
        assert any(c[0] == "commit" for c in conn.calls)

    def test_retention_days_passed_to_query(self):
        conn = _FakeConn([])
        prune_reports(conn=conn, remover=_RecordingRemover(), retention_days=90, apply=False)
        select = next(c for c in conn.calls if c[0] == "execute")
        assert select[2] == (90,)

    def test_nothing_expired_is_a_noop(self):
        conn, remover = _FakeConn([]), _RecordingRemover()
        acted = prune_reports(conn=conn, remover=remover, retention_days=365, apply=True)
        assert acted == []
        assert remover.removed == []


# ---------------------------------------------------------------------------
# 2. Storage remover HTTP contract
# ---------------------------------------------------------------------------


class TestStorageRemover:
    def test_issues_authorised_delete(self):
        seen: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["method"] = request.method
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization")
            seen["apikey"] = request.headers.get("apikey")
            return httpx.Response(200)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        remover = SupabaseStorageRemover(
            base_url="https://proj.supabase.co", service_role_key="svc-key", client=client
        )
        remover.remove(bucket="reports", path="firm-a/rep-1.pdf")
        assert seen["method"] == "DELETE"
        assert seen["url"] == "https://proj.supabase.co/storage/v1/object/reports/firm-a/rep-1.pdf"
        assert seen["auth"] == "Bearer svc-key"
        assert seen["apikey"] == "svc-key"

    def test_http_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        remover = SupabaseStorageRemover(
            base_url="https://proj.supabase.co", service_role_key="svc-key", client=client
        )
        with pytest.raises(httpx.HTTPStatusError):
            remover.remove(bucket="reports", path="firm-a/rep-1.pdf")


# ---------------------------------------------------------------------------
# 3. CLI guard
# ---------------------------------------------------------------------------


class TestCli:
    def test_missing_env_exits_2(self, monkeypatch: pytest.MonkeyPatch):
        for var in ("SUPABASE_DB_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
            monkeypatch.delenv(var, raising=False)
        assert main([]) == 2

    def test_expired_report_is_frozen(self):
        report = ExpiredReport(report_id="r", storage_path="p")
        with pytest.raises(FrozenInstanceError):
            report.report_id = "x"  # type: ignore[misc]
