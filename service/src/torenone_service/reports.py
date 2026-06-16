"""Report building + storage abstractions (Task 4.4).

These are injectable interfaces so the route can be tested without WeasyPrint or a
real Supabase project:

  * :class:`ReportBuilder` — renders a DesignResult to PDF bytes. Production uses
    :class:`WeasyPrintReportBuilder` (kernel report engine); tests inject a fake.
  * :class:`ReportStore` — persists the PDF + run/report metadata. Production will
    use a Supabase-backed store (Phase 5); the default :class:`InMemoryReportStore`
    keeps everything in process and is enough for local/dev and tests.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from fastapi import Request
from torenone_kernel.models.results import DesignResult

from torenone_service.schemas import StoredReport


@runtime_checkable
class ReportBuilder(Protocol):
    def build_pdf(self, result: DesignResult) -> bytes: ...


class WeasyPrintReportBuilder:
    """Render the calc-package PDF via the kernel report engine (needs WeasyPrint)."""

    def build_pdf(self, result: DesignResult) -> bytes:
        # Imported lazily so constructing the app does not require WeasyPrint.
        from torenone_kernel.report.renderer import render_pdf

        return render_pdf(result)


@runtime_checkable
class ReportStore(Protocol):
    def save_report(
        self,
        *,
        user_id: str,
        project_id: str | None,
        result: DesignResult,
        pdf_bytes: bytes,
        mode: str = "design",
    ) -> StoredReport: ...


class InMemoryReportStore:
    """Default store — keeps PDFs in process. Supabase-backed store wired in 5.6."""

    def __init__(self) -> None:
        self.reports: dict[str, bytes] = {}

    def save_report(
        self,
        *,
        user_id: str,
        project_id: str | None,
        result: DesignResult,
        pdf_bytes: bytes,
        mode: str = "design",
    ) -> StoredReport:
        run_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        storage_path = f"reports/{user_id}/{run_id}.pdf"
        self.reports[report_id] = pdf_bytes
        return StoredReport(
            run_id=run_id,
            report_id=report_id,
            storage_path=storage_path,
            size_bytes=len(pdf_bytes),
        )


@runtime_checkable
class StorageUploader(Protocol):
    """Uploads bytes to an object-storage bucket at a given path."""

    def upload(self, *, bucket: str, path: str, data: bytes, content_type: str) -> None: ...


class SupabaseStorageUploader:
    """Upload to Supabase Storage via its REST API (server-side, service-role key)."""

    def __init__(self, *, base_url: str, service_role_key: str, client: Any | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key
        self._client = client  # injectable httpx.Client for tests

    def upload(self, *, bucket: str, path: str, data: bytes, content_type: str) -> None:
        import httpx

        client = self._client or httpx.Client(timeout=30.0)
        url = f"{self._base_url}/storage/v1/object/{bucket}/{path}"
        response = client.request(
            "POST",
            url,
            content=data,
            headers={
                "Authorization": f"Bearer {self._service_role_key}",
                "apikey": self._service_role_key,
                "Content-Type": content_type,
                "x-upsert": "true",  # overwrite if a re-run reuses the path
            },
        )
        response.raise_for_status()


class SupabaseReportStore:
    """Persist a design run to Supabase: PDF → private Storage bucket, rows → Postgres.

    The PDF is uploaded under ``<firm_id>/<report_id>.pdf`` (matching the Task 5.3
    Storage RLS path scope), then the ``runs`` + ``reports`` rows are written in one
    transaction. ``firm_id`` is resolved from the caller's ``profiles`` row, so a run
    is always attributed to the right tenant. Storage is written *before* the DB so a
    ``reports`` row can never reference a missing object.

    ``connect`` returns a fresh DB-API connection (psycopg) per call; ``uploader`` is
    the Storage adapter. Both are injected so the store is testable without a live
    Supabase project.
    """

    def __init__(
        self,
        *,
        connect: Callable[[], Any],
        uploader: StorageUploader,
        bucket: str = "reports",
    ) -> None:
        self._connect = connect
        self._uploader = uploader
        self._bucket = bucket

    def save_report(
        self,
        *,
        user_id: str,
        project_id: str | None,
        result: DesignResult,
        pdf_bytes: bytes,
        mode: str = "design",
    ) -> StoredReport:
        if not project_id:
            raise ValueError("project_id is required to persist a design run")

        from psycopg.types.json import Jsonb

        run_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                row = cur.execute(
                    "select firm_id from public.profiles where id = %s", (user_id,)
                ).fetchone()
                if row is None:
                    raise LookupError(f"no profile/firm for user {user_id}")
                firm_id = row[0]
                storage_path = f"{firm_id}/{report_id}.pdf"

                # Storage first — a reports row must never point at a missing object.
                self._uploader.upload(
                    bucket=self._bucket,
                    path=storage_path,
                    data=pdf_bytes,
                    content_type="application/pdf",
                )
                cur.execute(
                    "insert into public.runs "
                    "(id, project_id, firm_id, frame_spec, mode, status, rules_version, "
                    " passed, governing_utilisation, created_by) "
                    "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        run_id,
                        project_id,
                        firm_id,
                        Jsonb(result.frame_spec.model_dump(mode="json")),
                        mode,
                        "complete",
                        Jsonb(result.rules_version),
                        result.passed,
                        result.governing_utilisation,
                        user_id,
                    ),
                )
                cur.execute(
                    "insert into public.reports (id, run_id, firm_id, storage_path) "
                    "values (%s, %s, %s, %s)",
                    (report_id, run_id, firm_id, storage_path),
                )
            conn.commit()
        finally:
            conn.close()

        return StoredReport(
            run_id=run_id,
            report_id=report_id,
            storage_path=storage_path,
            size_bytes=len(pdf_bytes),
        )


# Bound how long a single design request will wait to acquire a DB connection. The
# store opens one short-lived connection per /design call (and closes it), so DB
# concurrency is bounded by the service's request concurrency (capped at the Fly edge
# — see docs/DB_OPS.md), not by a long-lived in-process pool. A finite connect-timeout
# means a saturated session-pooler surfaces as a fast 502 rather than a hung worker.
DB_CONNECT_TIMEOUT_S: int = int(
    os.environ.get("SUPABASE_DB_CONNECT_TIMEOUT_S", "").strip() or "10"
)
# Tags connections in the Supabase pooler / pg_stat_activity for observability.
DB_APPLICATION_NAME: str = (
    os.environ.get("SUPABASE_DB_APPLICATION_NAME", "").strip() or "torenone-service"
)


def report_store_from_env() -> ReportStore | None:
    """Build a Supabase-backed store from env, or None if not fully configured.

    Requires ``SUPABASE_DB_URL`` (direct Postgres connection), ``SUPABASE_URL`` and
    ``SUPABASE_SERVICE_ROLE_KEY`` (Storage REST). When any is absent the caller falls
    back to the in-process store, so local/dev and tests still work.

    Point ``SUPABASE_DB_URL`` at the Supabase **transaction pooler** (port 6543) in
    production so many short-lived service connections multiplex onto few Postgres
    backends — see ``docs/DB_OPS.md`` for sizing.
    """
    db_url = os.environ.get("SUPABASE_DB_URL")
    base_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not (db_url and base_url and service_role_key):
        return None

    import psycopg

    def connect() -> Any:
        return psycopg.connect(
            db_url,
            connect_timeout=DB_CONNECT_TIMEOUT_S,
            application_name=DB_APPLICATION_NAME,
        )

    uploader = SupabaseStorageUploader(base_url=base_url, service_role_key=service_role_key)
    return SupabaseReportStore(connect=connect, uploader=uploader)


def default_report_store() -> ReportStore:
    """The env-configured Supabase store, or the in-process store as a fallback."""
    return report_store_from_env() or InMemoryReportStore()


def get_report_builder(request: Request) -> ReportBuilder:
    """FastAPI dependency: the configured report builder."""
    builder: ReportBuilder = request.app.state.report_builder
    return builder


def get_report_store(request: Request) -> ReportStore:
    """FastAPI dependency: the configured report store."""
    store: ReportStore = request.app.state.report_store
    return store
