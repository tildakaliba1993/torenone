"""Contract tests for the auth → profile/firm bootstrap (Phase 5, Task 5.2).

No live Postgres here (no Docker), so we assert the migration's contract statically:
the `handle_new_user` trigger function exists, is hardened (SECURITY DEFINER + pinned
search_path), creates the `profiles` row keyed to the new auth user, links a firm, and
is wired to fire AFTER INSERT on `auth.users`.

sqlglot parses the CREATE FUNCTION but degrades CREATE TRIGGER to a generic Command, so
the trigger wiring is checked on the normalised SQL text.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import sqlglot
from sqlglot import exp

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _auth_migration_text() -> str:
    matches = sorted(MIGRATIONS_DIR.glob("*_auth_profile_trigger.sql"))
    assert matches, "expected the auth profile/firm trigger migration"
    return matches[-1].read_text()


def _normalised(sql: str) -> str:
    # Lowercase + collapse whitespace so substring checks are formatting-agnostic.
    return re.sub(r"\s+", " ", sql.lower()).strip()


@pytest.fixture(scope="module")
def sql() -> str:
    return _normalised(_auth_migration_text())


def test_defines_handle_new_user_function(sql: str) -> None:
    assert "function public.handle_new_user()" in sql
    # And sqlglot recognises it as a CREATE FUNCTION (valid Postgres DDL).
    stmts = sqlglot.parse(_auth_migration_text(), read="postgres")
    assert any(
        isinstance(s, exp.Create) and s.kind == "FUNCTION" for s in stmts
    ), "handle_new_user must be a CREATE FUNCTION"


def test_function_is_security_hardened(sql: str) -> None:
    # SECURITY DEFINER is required so the insert isn't blocked by RLS at sign-up;
    # the pinned empty search_path prevents definer-function hijacking.
    assert "security definer" in sql
    assert "set search_path = ''" in sql


def test_creates_profile_keyed_to_the_auth_user(sql: str) -> None:
    assert "insert into public.profiles" in sql
    # profiles.id must be the new auth user's id (profiles.id == auth.users.id).
    assert "new.id" in sql


def test_links_a_firm(sql: str) -> None:
    # Either creates a new firm (first user) or reuses an invited firm_id.
    assert "insert into public.firms" in sql
    assert "firm_id" in sql


def test_trigger_fires_after_insert_on_auth_users(sql: str) -> None:
    assert "after insert on auth.users" in sql
    assert "for each row" in sql
    assert "execute function public.handle_new_user" in sql
