"""Schema contract tests for the Supabase migrations (Phase 5, Task 5.1).

There is no live Postgres in this environment (no Docker), so instead of applying
the migration we **parse** it with sqlglot (Postgres dialect) and assert the schema
contract that the rest of Phase 5 depends on:

  * every migration file is syntactically valid Postgres (parses without error);
  * exactly the five Design §A.7 tables exist with their required columns;
  * the multi-tenant backbone holds — every non-root table carries ``firm_id`` and
    the foreign keys wire the tenant graph together (this is what the Task 5.4 RLS
    policies will filter on);
  * primary keys and the not-null tenancy columns are present.

This runs in the normal CI Python job — no database required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest
import sqlglot
from sqlglot import exp

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@dataclass
class Table:
    name: str
    columns: list[str] = field(default_factory=list)
    primary_key: str | None = None
    not_null: set[str] = field(default_factory=set)
    foreign_keys: dict[str, str] = field(default_factory=dict)  # column -> referenced table


def _migration_files() -> list[Path]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    assert files, f"expected at least one migration in {MIGRATIONS_DIR}"
    return files


def _parse_all() -> list[exp.Expression]:
    statements: list[exp.Expression] = []
    for path in _migration_files():
        # Raises on a syntax error — the headline guarantee (valid Postgres).
        statements.extend(sqlglot.parse(path.read_text(), read="postgres"))
    return statements


def _tables() -> dict[str, Table]:
    tables: dict[str, Table] = {}
    for stmt in _parse_all():
        if not (isinstance(stmt, exp.Create) and stmt.kind == "TABLE"):
            continue
        schema = stmt.find(exp.Schema)
        if schema is None:
            continue
        table = Table(name=schema.this.name)
        for cd in stmt.find_all(exp.ColumnDef):
            col = cd.name
            table.columns.append(col)
            for cons in cd.find_all(exp.ColumnConstraint):
                kind = cons.kind
                if isinstance(kind, exp.PrimaryKeyColumnConstraint):
                    table.primary_key = col
                elif isinstance(kind, exp.NotNullColumnConstraint):
                    table.not_null.add(col)
                elif isinstance(kind, exp.Reference):
                    ref = kind.find(exp.Table)
                    if ref is not None:
                        table.foreign_keys[col] = ref.name
        tables[table.name] = table
    return tables


# Design §A.7 — minimum required columns per table.
REQUIRED_COLUMNS = {
    "firms": {"id", "name"},
    "profiles": {"id", "firm_id", "name", "role"},
    "projects": {"id", "firm_id", "name", "created_by"},
    "runs": {"id", "project_id", "firm_id", "frame_spec", "status", "rules_version", "created_by", "created_at"},
    "reports": {"id", "run_id", "firm_id", "storage_path", "created_at"},
    # Paddle PAYG: one paid calc package unlocks a run's PDF (20260625120000_paddle_billing).
    "design_credits": {"id", "run_id", "firm_id", "created_at"},
    # Pilot access codes — auto-grant the pilot trial at sign-up (20260626120000_pilot_firms).
    "pilot_codes": {"id", "code", "complimentary_days", "active"},
}

# The tenant graph the RLS policies (5.4) rely on: column -> referenced table.
REQUIRED_FOREIGN_KEYS = {
    "profiles": {"id": "users", "firm_id": "firms"},
    "projects": {"firm_id": "firms", "created_by": "profiles"},
    "runs": {"project_id": "projects", "firm_id": "firms"},
    "reports": {"run_id": "runs", "firm_id": "firms"},
    "design_credits": {"run_id": "runs", "firm_id": "firms"},
}


def test_migrations_are_valid_postgres() -> None:
    # _parse_all raises on any syntax error; reaching here means every file parsed.
    assert _parse_all()


def test_migration_files_are_timestamp_prefixed() -> None:
    # Supabase orders migrations lexicographically by a numeric timestamp prefix.
    for path in _migration_files():
        prefix = path.name.split("_", 1)[0]
        assert prefix.isdigit() and len(prefix) >= 14, f"bad migration name: {path.name}"


def test_exactly_the_design_tables_exist() -> None:
    assert set(_tables()) == set(REQUIRED_COLUMNS)


@pytest.mark.parametrize("table_name", sorted(REQUIRED_COLUMNS))
def test_table_has_required_columns(table_name: str) -> None:
    table = _tables()[table_name]
    missing = REQUIRED_COLUMNS[table_name] - set(table.columns)
    assert not missing, f"{table_name} missing columns: {missing}"


@pytest.mark.parametrize("table_name", sorted(REQUIRED_COLUMNS))
def test_every_table_has_a_uuid_primary_key_id(table_name: str) -> None:
    assert _tables()[table_name].primary_key == "id"


def test_multi_tenant_backbone_firm_id_on_every_non_root_table() -> None:
    tables = _tables()
    for name in ("profiles", "projects", "runs", "reports"):
        assert "firm_id" in tables[name].columns, f"{name} must carry firm_id for RLS"
        assert "firm_id" in tables[name].not_null, f"{name}.firm_id must be NOT NULL"


@pytest.mark.parametrize("table_name", sorted(REQUIRED_FOREIGN_KEYS))
def test_foreign_keys_wire_the_tenant_graph(table_name: str) -> None:
    fks = _tables()[table_name].foreign_keys
    for column, referenced in REQUIRED_FOREIGN_KEYS[table_name].items():
        assert fks.get(column) == referenced, (
            f"{table_name}.{column} should reference {referenced}, got {fks.get(column)!r}"
        )


def test_profiles_id_is_the_auth_user_id() -> None:
    # profiles.id == auth.users.id is how a JWT's `sub` maps to a firm.
    assert _tables()["profiles"].foreign_keys.get("id") == "users"
