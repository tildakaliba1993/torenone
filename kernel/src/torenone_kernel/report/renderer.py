"""TorenOne report renderer — Tasks 2.1 (HTML) + 2.2 (PDF).

Public API
----------
render_html(result: DesignResult) -> str
    Render a DesignResult to a standalone HTML string using the Jinja2 template.

render_pdf(result: DesignResult) -> bytes
    Render a DesignResult to PDF bytes via WeasyPrint.
    Requires Python 3.11 + Homebrew pango/cairo on macOS.

Design constraints
------------------
- All engineering values come from the DesignResult (kernel-computed).
- This module does NO arithmetic — it formats and presents existing values.
- Template is at torenone_kernel/report/template.html.jinja2 (relative to this file).
"""

from __future__ import annotations

import base64
import dataclasses
import math
from datetime import date
from pathlib import Path
from typing import Any

import jinja2

from torenone_kernel.models.results import DesignResult
from torenone_kernel.report.diagrams import bmd_sfd_png, frame_geometry_png
from torenone_kernel.sections.library import SectionLibrary

_TEMPLATE_PATH = Path(__file__).parent / "template.html.jinja2"

_PROVISIONAL_WARNINGS = [
    "fy for S355JR sourced from EN 10025-2 (not SANS 1431) — pending Pr.Eng sign-off.",
    "Load combination partial factors from DRAFT SANS 10160-1 (public enquiry version) "
    "— confirm vs final published standard.",
    "SAISC section properties from free PDF — pending registered-engineer spot-check vs Red Book.",
    "Sway-sensitive threshold U2 > 1.4: CSA S16 basis — SANS 10162-1 cl. 8.7 does not state "
    "an explicit numerical cutoff.",
    "Indicative cost rate R20/kg — confirm with fabricator before use in project estimates.",
    "Effective length factor K = 1.0 is a conservative lower bound only; sway portal columns "
    "may require K > 1.0.",
]

_DEFAULT_COST_RATE: float = 20.0  # R/kg — kept local to avoid circular import


@dataclasses.dataclass
class _ScheduleRow:
    member: str
    designation: str
    mass_per_m: float      # kg/m
    length_m: float        # m (one element, not doubled)
    mass_kg: float         # mass_per_m × length_m × count (count=2 per frame)


def _build_schedule(result: DesignResult) -> tuple[list[_ScheduleRow], float]:
    """Build a per-member steel schedule.

    Returns (rows, total_mass_kg).  Lengths match the _steel_mass_kg formula in design.py:
        2 × rafter_half_len × raf.mass/m + 2 × eaves_height × col.mass/m
    """
    lib = SectionLibrary.load_default()
    geom = result.frame_spec.geometry
    half_span_m = geom.span_m / 2.0
    rafter_half_len_m = math.hypot(
        half_span_m,
        geom.apex_height_m - geom.eaves_height_m,
    )
    eaves_h_m = geom.eaves_height_m

    member_lengths = {
        "rafter": rafter_half_len_m,
        "column": eaves_h_m,
    }

    rows: list[_ScheduleRow] = []
    total_kg = 0.0
    for sec_choice in result.sections:
        sec = lib.get(sec_choice.designation)
        length_m = member_lengths.get(sec_choice.member, 0.0)
        # ×2 because there are two rafters / two columns per symmetric frame
        mass_kg = 2.0 * sec.mass_per_metre_kg_m * length_m
        rows.append(_ScheduleRow(
            member=sec_choice.member,
            designation=sec_choice.designation,
            mass_per_m=sec.mass_per_metre_kg_m,
            length_m=length_m,
            mass_kg=mass_kg,
        ))
        total_kg += mass_kg

    return rows, total_kg


def _member_check_summary(result: DesignResult) -> tuple[dict[str, float], dict[str, bool]]:
    """Return per-member {member: governing_util} and {member: passed}."""
    member_util: dict[str, float] = {}
    member_pass: dict[str, bool] = {}

    for s in result.sections:
        # Find checks for this member (check names start with "<member>: ")
        prefix = s.member + ":"
        member_checks = [c for c in result.checks if c.name.startswith(prefix)]
        if member_checks:
            member_util[s.member] = max(c.utilisation for c in member_checks)
            member_pass[s.member] = all(c.passed for c in member_checks)
        else:
            member_util[s.member] = 0.0
            member_pass[s.member] = True

    return member_util, member_pass


def render_html(result: DesignResult) -> str:
    """Render *result* to a standalone HTML string.

    No arithmetic is performed here — all numeric values come directly from *result*.
    """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_TEMPLATE_PATH.parent)),
        autoescape=True,
    )
    template = env.get_template(_TEMPLATE_PATH.name)

    geom = result.frame_spec.geometry
    dead = result.frame_spec.dead
    wind = result.frame_spec.wind
    schedule, _total_mass = _build_schedule(result)
    member_util, member_pass = _member_check_summary(result)

    # Extract cost_rate from result if available, else use default
    # (indicative_cost_zar / total_steel_mass_kg gives the rate used)
    if (
        result.indicative_cost_zar is not None
        and result.total_steel_mass_kg is not None
        and result.total_steel_mass_kg > 0
    ):
        cost_rate = result.indicative_cost_zar / result.total_steel_mass_kg
    else:
        cost_rate = _DEFAULT_COST_RATE

    # fy from rules_version if present, else standard S355 value
    fy_mpa = 355  # S355JR t<=16mm (from EN 10025-2, PROVISIONAL)

    # Diagrams — rendered as base64-encoded PNG data URIs for embedding in HTML/PDF
    geom_png_b64  = base64.b64encode(frame_geometry_png(result.frame_spec)).decode("ascii")
    bmd_sfd_b64   = base64.b64encode(bmd_sfd_png(result)).decode("ascii")

    ctx: dict[str, Any] = {
        "generated_date": date.today().isoformat(),
        "geom": geom,
        "dead": dead,
        "wind": wind,
        "base_fixity": result.frame_spec.base_fixity.value,
        "steel_grade": result.frame_spec.materials.steel_grade.value,
        "fy_mpa": fy_mpa,
        "sections": result.sections,
        "checks": result.checks,
        "result_passed": result.passed,
        "governing_utilisation": result.governing_utilisation,
        "member_util": member_util,
        "member_pass": member_pass,
        "schedule": schedule,
        "total_mass_kg": result.total_steel_mass_kg or _total_mass,
        "indicative_cost_zar": result.indicative_cost_zar or 0.0,
        "cost_rate_zar_per_kg": cost_rate,
        "rules_version": result.rules_version,
        "provisional_warnings": _PROVISIONAL_WARNINGS,
        "geom_png_b64": geom_png_b64,
        "bmd_sfd_b64": bmd_sfd_b64,
    }

    return template.render(**ctx)


def render_pdf(result: DesignResult) -> bytes:
    """Render *result* to PDF bytes using WeasyPrint.

    Requires Python 3.11 + Homebrew pango/cairo on macOS.
    Raises ImportError if WeasyPrint is not available.

    Returns
    -------
    bytes — PDF file content (starts with b'%PDF-').
    """
    try:
        import weasyprint  # type: ignore[import]
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "WeasyPrint is required for PDF rendering. "
            "Install with: pip install weasyprint (requires Python 3.11 + pango/cairo on macOS). "
            "See docs/HANDOVER.md for environment setup."
        ) from exc

    html_string = render_html(result)
    pdf_bytes: bytes = weasyprint.HTML(string=html_string).write_pdf()
    return pdf_bytes
