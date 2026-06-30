"""Render a registered-engineer-stamped calc package for a stored run (T1-1).

A stamp re-renders the run's PDF with the engineer's e-stamp filled in. The stored
``runs.result`` JSON carries computed fields that the strict kernel models reject on input,
so the DesignResult is reconstructed by **re-running the deterministic kernel** from the run's
stored ``frame_spec`` (+ sections for check mode) — which reproduces an identical result and
fingerprint. The stamp records that a named ECSA-registered engineer accepted professional
responsibility; it is NOT a claim that TorenOne validated anything.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from torenone_kernel.report.metadata import ReportMetadata, Stamp
from torenone_kernel.report.renderer import render_pdf, report_fingerprint

from torenone_service.design_service import DesignError, run_design
from torenone_service.schemas import DesignRequest


class StampError(Exception):
    """A stamp could not be produced (bad/unreproducible stored run)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp, matching the report's date format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_stamped_pdf(
    *,
    frame_spec: dict[str, Any],
    mode: str,
    result: dict[str, Any],
    report_metadata: dict[str, Any] | None,
    engineer_name: str,
    ecsa_reg_no: str,
    stamped_at: str,
) -> tuple[bytes, Stamp]:
    """Re-render *result*'s calc package with the engineer e-stamp; return (pdf, stamp).

    Reconstructs the DesignResult by re-running the kernel on the stored inputs (deterministic),
    so the stamp's fingerprint equals the original report fingerprint.
    """
    sections_raw = result.get("sections") if mode == "check" else None

    # Preserve the original cost rate so the re-rendered cost is identical.
    cost = result.get("indicative_cost_zar")
    mass = result.get("total_steel_mass_kg")
    rate = (cost / mass) if (cost and mass) else None

    try:
        # model_validate (not the constructor) so the spec dict flows through the schema's
        # computed-geometry stripper before FrameSpec validation.
        request = DesignRequest.model_validate(
            {
                "spec": frame_spec,
                "mode": "check" if mode == "check" else "design",
                "sections": sections_raw,
                "cost_rate_zar_per_kg": rate,
            }
        )
        design_result = run_design(request)
    except (DesignError, ValueError) as exc:
        raise StampError(f"could not reproduce the design to stamp: {exc}") from exc

    stamp = Stamp(
        engineer_name=engineer_name,
        ecsa_reg_no=ecsa_reg_no,
        stamped_at=stamped_at,
        fingerprint=report_fingerprint(design_result),
    )
    metadata = ReportMetadata.model_validate(report_metadata) if report_metadata else None
    pdf_bytes = render_pdf(design_result, metadata, stamp)
    return pdf_bytes, stamp
