"""Behavioural multi-tenant isolation test (Phase 5, Task 5.4) — PRD FR-23 / §9.

THE multi-tenant safety gate: prove, against a real Postgres with RLS enforced, that
a user in firm A cannot read, insert, update or delete firm B's data — and vice-versa.

How it works without the Supabase stack:
  * connect to ``DATABASE_URL`` (a throwaway Postgres where we are superuser),
  * apply ``harness/00_supabase_stubs.sql`` (auth/storage schemas, roles, ``auth.uid()``)
    then every real migration in order — so the production RLS policies run verbatim,
  * seed two firms via the real sign-up trigger (insert two ``auth.users``),
  * act as each user with ``SET ROLE authenticated`` + their JWT ``sub`` claim and assert
    the isolation in both directions.

Skips cleanly when no Postgres is available (e.g. a plain ``pytest`` with no DB), so it
never blocks local runs; CI provides a Postgres service so it runs for real there.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

_HERE = Path(__file__).resolve().parent
_MIGRATIONS = sorted((_HERE.parent / "migrations").glob("*.sql"))
_HARNESS = _HERE / "harness" / "00_supabase_stubs.sql"
_DB_URL = os.environ.get("DATABASE_URL") or os.environ.get("TORENONE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not _DB_URL, reason="no DATABASE_URL — RLS isolation test needs a Postgres")


@dataclass(frozen=True)
class Seed:
    user_a: UUID
    user_b: UUID
    firm_a: UUID
    firm_b: UUID


@pytest.fixture(scope="module")
def conn():  # type: ignore[no-untyped-def]
    try:
        connection = psycopg.connect(_DB_URL, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"cannot connect to DATABASE_URL: {exc}")

    # Rebuild a pristine schema, then apply the harness + every real migration.
    with connection.cursor() as cur:
        cur.execute("drop schema if exists public cascade; create schema public;")
        cur.execute("drop schema if exists auth cascade;")
        cur.execute("drop schema if exists storage cascade;")
        cur.execute(_HARNESS.read_text())
        for migration in _MIGRATIONS:
            cur.execute(migration.read_text())
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def seed(conn) -> Seed:  # type: ignore[no-untyped-def]
    user_a, user_b = uuid4(), uuid4()
    with conn.cursor() as cur:
        # Two sign-ups → the Task 5.2 trigger creates a firm + profile for each.
        cur.execute(
            "insert into auth.users (id, email, raw_user_meta_data) values "
            "(%s, %s, %s), (%s, %s, %s)",
            (user_a, "a@firm-a.test", '{"firm_name":"Firm A"}',
             user_b, "b@firm-b.test", '{"firm_name":"Firm B"}'),
        )
        firm_a = cur.execute("select firm_id from public.profiles where id = %s", (user_a,)).fetchone()[0]
        firm_b = cur.execute("select firm_id from public.profiles where id = %s", (user_b,)).fetchone()[0]
        # A project + run + report in each firm.
        for firm, user, tag in ((firm_a, user_a, "A"), (firm_b, user_b, "B")):
            proj = uuid4()
            run = uuid4()
            cur.execute(
                "insert into public.projects (id, firm_id, name, created_by) values (%s, %s, %s, %s)",
                (proj, firm, f"Project {tag}", user),
            )
            cur.execute(
                "insert into public.runs (id, project_id, firm_id, frame_spec, created_by) "
                "values (%s, %s, %s, %s::jsonb, %s)",
                (run, proj, firm, "{}", user),
            )
            cur.execute(
                "insert into public.reports (id, run_id, firm_id, storage_path) values (%s, %s, %s, %s)",
                (uuid4(), run, firm, f"{firm}/calc.pdf"),
            )
    assert firm_a != firm_b
    return Seed(user_a=user_a, user_b=user_b, firm_a=firm_a, firm_b=firm_b)


def _act(conn, uid, sql, params=(), *, fetch=True):  # type: ignore[no-untyped-def]
    """Run ``sql`` as role ``authenticated`` with JWT sub=``uid``; always rolls back."""
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("set local role authenticated")
            cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(uid) if uid else "",))
            cur.execute(sql, params)
            return cur.fetchall() if fetch else cur.rowcount
    finally:
        conn.rollback()
        conn.autocommit = True


# Each row: (table, the firm column to compare). Reports/runs/projects all carry firm_id.
_FIRM_TABLES = ["projects", "runs", "reports", "profiles", "firms"]


@pytest.mark.parametrize("table", _FIRM_TABLES)
def test_user_sees_only_their_own_firm_rows(conn, seed: Seed, table: str) -> None:  # type: ignore[no-untyped-def]
    column = "id" if table == "firms" else "firm_id"
    a_rows = _act(conn, seed.user_a, f"select {column} from public.{table}")
    b_rows = _act(conn, seed.user_b, f"select {column} from public.{table}")
    assert {r[0] for r in a_rows} == {seed.firm_a}, f"firm A leaked rows from {table}: {a_rows}"
    assert {r[0] for r in b_rows} == {seed.firm_b}, f"firm B leaked rows from {table}: {b_rows}"


@pytest.mark.parametrize("table", ["projects", "runs", "reports"])
def test_cross_firm_read_returns_nothing(conn, seed: Seed, table: str) -> None:  # type: ignore[no-untyped-def]
    rows = _act(conn, seed.user_a, f"select * from public.{table} where firm_id = %s", (seed.firm_b,))
    assert rows == [], f"firm A could read firm B rows from {table}"


def test_cross_firm_insert_is_blocked(conn, seed: Seed) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(psycopg.Error):
        _act(
            conn, seed.user_a,
            "insert into public.projects (firm_id, name, created_by) values (%s, %s, %s)",
            (seed.firm_b, "intrusion", seed.user_a), fetch=False,
        )


@pytest.mark.parametrize("table", ["projects", "runs", "reports"])
def test_cross_firm_update_affects_no_rows(conn, seed: Seed, table: str) -> None:  # type: ignore[no-untyped-def]
    affected = _act(
        conn, seed.user_a,
        f"update public.{table} set firm_id = firm_id where firm_id = %s",
        (seed.firm_b,), fetch=False,
    )
    assert affected == 0, f"firm A could update firm B rows in {table}"


@pytest.mark.parametrize("table", ["projects", "runs", "reports"])
def test_cross_firm_delete_affects_no_rows(conn, seed: Seed, table: str) -> None:  # type: ignore[no-untyped-def]
    affected = _act(
        conn, seed.user_a,
        f"delete from public.{table} where firm_id = %s",
        (seed.firm_b,), fetch=False,
    )
    assert affected == 0, f"firm A could delete firm B rows in {table}"


def test_user_can_write_within_their_own_firm(conn, seed: Seed) -> None:  # type: ignore[no-untyped-def]
    # Positive control — the policies don't block legitimate same-firm writes.
    affected = _act(
        conn, seed.user_a,
        "insert into public.projects (firm_id, name, created_by) values (%s, %s, %s)",
        (seed.firm_a, "legit", seed.user_a), fetch=False,
    )
    assert affected == 1


def test_unauthenticated_sees_no_rows(conn, seed: Seed) -> None:  # type: ignore[no-untyped-def]
    # No JWT sub → current_firm_id() is null → every firm_id comparison is false.
    assert _act(conn, None, "select * from public.projects") == []
