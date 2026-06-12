"""Contract tests for report-PDF storage (Phase 5, Task 5.3).

No live Postgres/Storage here, so we assert the migration's contract statically:
a PRIVATE `reports` bucket exists, the shared `current_firm_id()` helper is defined
and hardened, and the Storage RLS policies scope every read/write/delete to the
caller's own `<firm_id>/` path prefix (so one firm can never reach another's PDFs).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _storage_migration_text() -> str:
    matches = sorted(MIGRATIONS_DIR.glob("*_storage_reports_bucket.sql"))
    assert matches, "expected the storage reports-bucket migration"
    return matches[-1].read_text()


def _normalised(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.lower()).strip()


@pytest.fixture(scope="module")
def sql() -> str:
    return _normalised(_storage_migration_text())


def test_creates_a_private_reports_bucket(sql: str) -> None:
    assert "insert into storage.buckets" in sql
    # id/name 'reports', public = false → a private bucket (no public URLs).
    assert "values ('reports', 'reports', false)" in sql


def test_defines_hardened_current_firm_id_helper(sql: str) -> None:
    assert "function public.current_firm_id()" in sql
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    # Resolves the caller's firm from their profile.
    assert "from public.profiles" in sql
    assert "auth.uid()" in sql


def test_policies_target_storage_objects_for_authenticated(sql: str) -> None:
    assert "on storage.objects" in sql
    assert "to authenticated" in sql


def test_policies_scope_to_the_callers_firm_folder(sql: str) -> None:
    # The per-firm isolation predicate: first path segment must equal the firm_id.
    predicate = "(storage.foldername(name))[1] = public.current_firm_id()"
    assert predicate in sql
    assert "bucket_id = 'reports'" in sql


@pytest.mark.parametrize("action", ["for select", "for insert", "for delete"])
def test_read_write_delete_are_all_scoped(action: str, sql: str) -> None:
    assert action in sql, f"expected a policy {action} on storage.objects"


def test_insert_policy_uses_with_check(sql: str) -> None:
    # INSERT scoping must be a WITH CHECK (USING does not apply to inserts).
    assert "with check" in sql
