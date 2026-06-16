"""Report-PDF retention/lifecycle pruner (Production-Readiness §6.2).

Calc-package PDFs in the private ``reports`` Storage bucket (plus their ``reports``
rows) accumulate forever today. This script enforces a retention window: any report
whose run is older than ``REPORT_RETENTION_DAYS`` is deleted — **Storage object first,
then the DB row**, so a ``reports`` row never points at a missing object and a crash
mid-run is safely re-runnable (idempotent).

It is **dry-run by default** (lists what *would* be deleted); pass ``--apply`` to
actually delete. Intended to run on a schedule (cron / a GitHub Actions cron / a
Supabase scheduled task) — see ``docs/DATA_RETENTION.md``.

Design mirrors :class:`torenone_service.reports.SupabaseReportStore`: the DB
connection factory and the Storage remover are injected, so the core pruning logic is
unit-tested without a live Supabase project.

Usage:
    SUPABASE_DB_URL=... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
        python tools/prune_reports.py [--days 365] [--apply]
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

DEFAULT_RETENTION_DAYS = 365
BUCKET = "reports"


@dataclass(frozen=True)
class ExpiredReport:
    """A report due for deletion."""

    report_id: str
    storage_path: str


@runtime_checkable
class StorageRemover(Protocol):
    """Deletes an object from a Storage bucket."""

    def remove(self, *, bucket: str, path: str) -> None: ...


class SupabaseStorageRemover:
    """Delete an object from Supabase Storage via its REST API (service-role)."""

    def __init__(self, *, base_url: str, service_role_key: str, client: Any | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key
        self._client = client  # injectable httpx.Client for tests

    def remove(self, *, bucket: str, path: str) -> None:
        import httpx

        client = self._client or httpx.Client(timeout=30.0)
        url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        response = client.request(
            "DELETE",
            url,
            headers={
                "Authorization": f"Bearer {self._service_role_key}",
                "apikey": self._service_role_key,
            },
        )
        response.raise_for_status()


def find_expired_reports(conn: Any, *, retention_days: int) -> list[ExpiredReport]:
    """Return reports whose owning run is older than *retention_days*."""
    with conn.cursor() as cur:
        rows = cur.execute(
            "select r.id, r.storage_path "
            "from public.reports r join public.runs run on run.id = r.run_id "
            "where run.created_at < now() - make_interval(days => %s) "
            "order by run.created_at asc",
            (retention_days,),
        ).fetchall()
    return [ExpiredReport(report_id=str(row[0]), storage_path=str(row[1])) for row in rows]


def prune_reports(
    *,
    conn: Any,
    remover: StorageRemover,
    retention_days: int,
    apply: bool,
) -> list[ExpiredReport]:
    """Delete (or, in dry-run, list) reports past the retention window.

    For each expired report the Storage object is removed first, then the ``reports``
    row — order chosen so a row never outlives its object. Returns the reports acted on
    (the would-delete set in dry-run). Idempotent: a re-run after a partial failure
    simply re-deletes whatever remains.
    """
    expired = find_expired_reports(conn, retention_days=retention_days)
    if not apply:
        return expired

    for report in expired:
        remover.remove(bucket=BUCKET, path=report.storage_path)
        with conn.cursor() as cur:
            cur.execute("delete from public.reports where id = %s", (report.report_id,))
        conn.commit()
    return expired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prune expired report PDFs (§6.2 retention).")
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.environ.get("REPORT_RETENTION_DAYS", "").strip() or DEFAULT_RETENTION_DAYS),
        help="Retention window in days (default: REPORT_RETENTION_DAYS or 365).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete. Without this flag the script only lists (dry-run).",
    )
    args = parser.parse_args(argv)

    db_url = os.environ.get("SUPABASE_DB_URL")
    base_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (db_url and base_url and service_role_key):
        print(
            "error: SUPABASE_DB_URL, SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set",
            file=sys.stderr,
        )
        return 2

    import psycopg

    remover = SupabaseStorageRemover(base_url=base_url, service_role_key=service_role_key)
    conn = psycopg.connect(db_url)
    try:
        acted = prune_reports(
            conn=conn, remover=remover, retention_days=args.days, apply=args.apply
        )
    finally:
        conn.close()

    verb = "Deleted" if args.apply else "Would delete"
    print(f"{verb} {len(acted)} report(s) older than {args.days} day(s).")
    for report in acted:
        print(f"  {report.report_id}  {report.storage_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
