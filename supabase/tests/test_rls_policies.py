"""Static contract tests for Row-Level Security (Phase 5, Task 5.4).

These run everywhere (no database needed) and guarantee the RLS migration *exists*
and is shaped correctly — RLS enabled on every table, policies filtered by
`current_firm_id()`. The behavioural proof that isolation actually holds lives in
``test_rls_isolation.py`` (which runs against a real Postgres).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
TABLES = ["firms", "profiles", "projects", "runs", "reports"]
CRUD_TABLES = ["projects", "runs", "reports"]


def _rls_migration_text() -> str:
    matches = sorted(MIGRATIONS_DIR.glob("*_rls_policies.sql"))
    assert matches, "expected the RLS policies migration"
    return matches[-1].read_text()


@pytest.fixture(scope="module")
def sql() -> str:
    return re.sub(r"\s+", " ", _rls_migration_text().lower()).strip()


@pytest.mark.parametrize("table", TABLES)
def test_rls_enabled_on_every_table(table: str, sql: str) -> None:
    assert f"alter table public.{table} enable row level security" in sql


def test_policies_filter_by_current_firm_id(sql: str) -> None:
    assert "public.current_firm_id()" in sql


@pytest.mark.parametrize("table", TABLES)
def test_every_table_has_a_select_policy(table: str, sql: str) -> None:
    assert f"on public.{table} for select" in sql


@pytest.mark.parametrize("table", CRUD_TABLES)
@pytest.mark.parametrize("action", ["insert", "update", "delete"])
def test_crud_tables_have_write_policies(table: str, action: str, sql: str) -> None:
    assert f"on public.{table} for {action}" in sql


@pytest.mark.parametrize("action", ["insert", "update", "delete"])
def test_write_policies_have_with_check_or_using(action: str, sql: str) -> None:
    # insert/update guard the new row with WITH CHECK; update/delete filter with USING.
    if action == "insert":
        assert "for insert to authenticated with check" in sql
    else:
        assert f"for {action} to authenticated using" in sql
