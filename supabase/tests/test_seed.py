"""Tests for the dev/seed data (Phase 5, Task 5.5).

Static contract checks run everywhere; the behavioural check applies the harness +
migrations + seed.sql to a real Postgres and proves the dev firm/user/project are
created, idempotently, and that the seeded user is RLS-scoped to its own firm.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SEED = _HERE.parent / "seed.sql"
_HARNESS = _HERE / "harness" / "00_supabase_stubs.sql"
_MIGRATIONS = sorted((_HERE.parent / "migrations").glob("*.sql"))
_DB_URL = os.environ.get("DATABASE_URL") or os.environ.get("TORENONE_TEST_DATABASE_URL")

DEV_USER = "11111111-1111-1111-1111-111111111111"
DEV_PROJECT = "22222222-2222-2222-2222-222222222222"


# --------------------------------------------------------------------------- #
# Static contract (no database)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def seed_sql() -> str:
    assert _SEED.is_file(), "expected supabase/seed.sql"
    return re.sub(r"\s+", " ", _SEED.read_text().lower()).strip()


def test_seed_creates_the_dev_user(seed_sql: str) -> None:
    assert "insert into auth.users" in seed_sql
    assert "dev@torenone.test" in seed_sql


def test_seed_user_has_a_password_and_is_confirmed(seed_sql: str) -> None:
    # A real bcrypt password + confirmed email so the dev user can actually sign in.
    assert "crypt(" in seed_sql
    assert "email_confirmed_at" in seed_sql


def test_seed_drives_firm_creation_through_the_trigger(seed_sql: str) -> None:
    # firm_name metadata → the Task 5.2 trigger makes the firm + profile.
    assert '"firm_name"' in seed_sql or "firm_name" in seed_sql


def test_seed_is_idempotent(seed_sql: str) -> None:
    assert "on conflict (id) do nothing" in seed_sql


def test_seed_adds_a_sample_project(seed_sql: str) -> None:
    assert "insert into public.projects" in seed_sql


def test_seed_is_marked_local_only(seed_sql: str) -> None:
    assert "local development only" in seed_sql


# --------------------------------------------------------------------------- #
# Behavioural (real Postgres; skipped without DATABASE_URL)
# --------------------------------------------------------------------------- #
psycopg = pytest.importorskip("psycopg")

_db = pytest.mark.skipif(not _DB_URL, reason="no DATABASE_URL — seed behaviour test needs a Postgres")


@pytest.fixture(scope="module")
def seeded_conn():  # type: ignore[no-untyped-def]
    try:
        conn = psycopg.connect(_DB_URL, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"cannot connect to DATABASE_URL: {exc}")
    with conn.cursor() as cur:
        cur.execute("drop schema if exists public cascade; create schema public;")
        cur.execute("drop schema if exists auth cascade;")
        cur.execute("drop schema if exists storage cascade;")
        cur.execute(_HARNESS.read_text())
        for migration in _MIGRATIONS:
            cur.execute(migration.read_text())
        cur.execute(_SEED.read_text())  # apply once
        cur.execute(_SEED.read_text())  # apply again — must be idempotent
    yield conn
    conn.close()


@_db
def test_seed_creates_exactly_one_firm_profile_project(seeded_conn) -> None:  # type: ignore[no-untyped-def]
    with seeded_conn.cursor() as cur:
        assert cur.execute("select count(*) from public.firms").fetchone()[0] == 1
        assert cur.execute("select count(*) from public.profiles").fetchone()[0] == 1
        assert cur.execute("select count(*) from public.projects").fetchone()[0] == 1
        assert cur.execute("select count(*) from public.runs").fetchone()[0] == 1


@_db
def test_seeded_user_is_loginable(seeded_conn) -> None:  # type: ignore[no-untyped-def]
    with seeded_conn.cursor() as cur:
        row = cur.execute(
            "select encrypted_password, email_confirmed_at from auth.users where id = %s",
            (DEV_USER,),
        ).fetchone()
    assert row is not None
    assert row[0] is not None and row[1] is not None  # password set + email confirmed


@_db
def test_seeded_user_sees_its_own_project_under_rls(seeded_conn) -> None:  # type: ignore[no-untyped-def]
    seeded_conn.autocommit = False
    try:
        with seeded_conn.cursor() as cur:
            cur.execute("set local role authenticated")
            cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (DEV_USER,))
            rows = cur.execute("select id from public.projects").fetchall()
    finally:
        seeded_conn.rollback()
        seeded_conn.autocommit = True
    assert [str(r[0]) for r in rows] == [DEV_PROJECT]
