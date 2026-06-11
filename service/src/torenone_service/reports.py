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

import uuid
from typing import Protocol, runtime_checkable

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
    ) -> StoredReport: ...


class InMemoryReportStore:
    """Default store — keeps PDFs in process. Swapped for Supabase in Phase 5."""

    def __init__(self) -> None:
        self.reports: dict[str, bytes] = {}

    def save_report(
        self,
        *,
        user_id: str,
        project_id: str | None,
        result: DesignResult,
        pdf_bytes: bytes,
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


def get_report_builder(request: Request) -> ReportBuilder:
    """FastAPI dependency: the configured report builder."""
    builder: ReportBuilder = request.app.state.report_builder
    return builder


def get_report_store(request: Request) -> ReportStore:
    """FastAPI dependency: the configured report store."""
    store: ReportStore = request.app.state.report_store
    return store
