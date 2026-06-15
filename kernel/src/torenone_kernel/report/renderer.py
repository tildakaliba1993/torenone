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
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jinja2

from torenone_kernel.analysis.plane_frame import PortalAnalysis
from torenone_kernel.checks.axial import cr_flexural
from torenone_kernel.checks.bending import mcr_elastic, mr_ltb
from torenone_kernel.checks.classification import classify_section
from torenone_kernel.checks.material import fy_mpa as _fy_mpa
from torenone_kernel.checks.shear import vr_web
from torenone_kernel.loads.combinations import load_combinations
from torenone_kernel.loads.dead import dead_loads
from torenone_kernel.loads.imposed import imposed_roof_loads
from torenone_kernel.models.results import DesignResult
from torenone_kernel.report.diagrams import bmd_sfd_png, frame_geometry_png
from torenone_kernel.sections.library import SectionLibrary

_TEMPLATE_PATH = Path(__file__).parent / "template.html.jinja2"

_PROVISIONAL_WARNINGS = [
    "SAISC section properties from free PDF — pending registered-engineer spot-check vs Red Book.",
    "Sway-sensitive threshold U2 > 1.4: CSA S16 basis — SANS 10162-1 cl. 8.7 does not state "
    "an explicit numerical cutoff.",
    "Indicative cost rate R20/kg — confirm with fabricator before use in project estimates.",
    "Effective length factor K = 1.0 is a conservative lower bound only; sway portal columns "
    "may require K > 1.0.",
]

_DEFAULT_COST_RATE: float = 20.0  # R/kg — kept local to avoid circular import

# ---- Status rendering (PRD FR-19) ----------------------------------------
# Three-tier status: PASS / NEAR LIMIT / FAIL.
# "Near limit" = utilisation ≥ threshold AND ≤ 1.0 — warrants engineer attention
# but does not constitute a code failure.
# Threshold of 0.85 (within 15 % of capacity) is a widely-used engineering convention;
# no SANS clause mandates a specific threshold so this is a display-layer choice.
NEAR_LIMIT_THRESHOLD: float = 0.85

# Check-name prefixes for the "last mile" details (rendered in their own report
# sections, so they are excluded from the main member code-checks table).
_DETAIL_CHECK_PREFIXES: tuple[str, ...] = ("connection:", "baseplate:", "footing:")


# ---- Audit fingerprint (PRD FR-20) ---------------------------------------

def report_fingerprint(result: DesignResult) -> str:
    """Return a deterministic SHA-256 fingerprint of *result*.

    The fingerprint is the hex digest of SHA-256(canonical JSON) where
    canonical JSON = ``json.dumps(result.model_dump(mode="json"),
    sort_keys=True, separators=(",", ":"))`` encoded as UTF-8.

    Properties:
    - Identical DesignResult → identical fingerprint (determinism guarantee).
    - Any change to any field → different fingerprint.
    - Embeddable in the report for reproducibility and audit traceability (FR-20).
    """
    canonical = json.dumps(
        result.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
        # Find the GATING checks for this member (check names start with "<member>: ").
        # Advisory/informational checks (e.g. the provisional ULS/SLS wind checks) are
        # excluded from the member pass/fail summary — they render in the checks table only.
        prefix = s.member + ":"
        member_checks = [
            c for c in result.checks if c.name.startswith(prefix) and not c.informational
        ]
        if member_checks:
            member_util[s.member] = max(c.utilisation for c in member_checks)
            member_pass[s.member] = all(c.passed for c in member_checks)
        else:
            member_util[s.member] = 0.0
            member_pass[s.member] = True

    return member_util, member_pass


@dataclasses.dataclass
class _MemberWorking:
    """Intermediate capacity values for one member — for show-your-working."""
    member: str
    designation: str
    section_class: int
    area_mm2: float
    ix_mm4: float
    iy_mm4: float
    zpl_mm3: float
    ry_mm: float
    fy_mpa: float
    KL_mm: float
    kl_over_r: float
    cr_kn: float
    hw_mm: float
    vr_kn: float
    LTB_mm: float
    mcr_knm: float
    mr_knm: float


def _compute_working(result: DesignResult) -> dict[str, Any]:
    """Compute all intermediate values for the show-your-working section (FR-26).

    Re-runs relevant kernel functions from DesignResult.frame_spec + chosen sections.
    All values are kernel-computed; this function does NO arithmetic.
    Returns a dict suitable for passing directly into the Jinja2 template context.
    """
    spec = result.frame_spec
    geom = spec.geometry
    lib = SectionLibrary.load_default()
    sec_map = {s.member: lib.get(s.designation) for s in result.sections}
    col_sec = sec_map["column"]
    raf_sec = sec_map["rafter"]

    # ---- Characteristic loads ----
    dead = dead_loads(spec, rafter=raf_sec, column=col_sec)
    imp  = imposed_roof_loads(spec)

    # ---- Load combinations ----
    combos_list = load_combinations(spec)
    uls1 = next(c for c in combos_list if c.name.startswith("ULS-1"))
    gamma_G = uls1.factors["dead"]
    gamma_Q = uls1.factors.get("imposed", 0.0)

    uls_raf_udl = gamma_G * dead.rafter_udl_kn_per_m + gamma_Q * imp.roof_udl_kn_per_m
    uls_col_udl = gamma_G * (dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m)

    # ---- Analysis forces ----
    analysis = PortalAnalysis(spec, col_sec, raf_sec).run(
        uls1.name, uls_raf_udl, uls_col_udl
    )
    forces = {f.location: f for f in analysis.forces}

    # ---- Member lengths ----
    half_mm = geom.span_m / 2.0 * 1_000.0
    rise_mm = (geom.apex_height_m - geom.eaves_height_m) * 1_000.0
    raf_len_mm = math.hypot(half_mm, rise_mm)
    col_len_mm = geom.eaves_height_m * 1_000.0

    # ---- Section capacities (per member) ----
    member_workings: list[_MemberWorking] = []
    for member, sec, KL_mm, LTB_mm in [
        ("rafter", raf_sec, raf_len_mm, raf_len_mm),
        ("column", col_sec, col_len_mm, col_len_mm),
    ]:
        fy = _fy_mpa(spec.materials.steel_grade, sec.flange_thickness_mm)
        cls = classify_section(sec, fy, 0.0)
        cr = cr_flexural(sec.area_mm2, fy, KL_mm, sec.radius_gyration_ry_mm)
        hw_mm = sec.depth_mm - 2.0 * sec.flange_thickness_mm
        vr = vr_web(hw_mm, sec.web_thickness_mm, fy)
        mcr = mcr_elastic(LTB_mm, sec.second_moment_iy_mm4,
                          sec.torsion_constant_j_mm4, sec.warping_constant_cw_mm6, 1.0)
        mr = mr_ltb(cls.overall_class, sec.plastic_modulus_zx_mm3,
                    sec.elastic_modulus_sx_mm3, fy, mcr)
        kl_r = KL_mm / sec.radius_gyration_ry_mm

        member_workings.append(_MemberWorking(
            member=member,
            designation=sec.designation,
            section_class=int(cls.overall_class),
            area_mm2=sec.area_mm2,
            ix_mm4=sec.second_moment_ix_mm4,
            iy_mm4=sec.second_moment_iy_mm4,
            zpl_mm3=sec.plastic_modulus_zx_mm3,
            ry_mm=sec.radius_gyration_ry_mm,
            fy_mpa=fy,
            KL_mm=KL_mm,
            kl_over_r=kl_r,
            cr_kn=cr,
            hw_mm=hw_mm,
            vr_kn=vr,
            LTB_mm=LTB_mm,
            mcr_knm=mcr,
            mr_knm=mr,
        ))

    return {
        # Dead loads
        "w_dead": dead,
        "dead_rafter_area_load_kpa": dead.roof_area_load_kpa,
        "dead_trib_width_m": dead.tributary_width_m,
        "dead_rafter_sw_kn_m": dead.rafter_self_weight_kn_per_m,
        "dead_rafter_udl_kn_m": dead.rafter_udl_kn_per_m,
        "dead_col_sw_kn_m": dead.column_self_weight_kn_per_m,
        "dead_wall_kn_m": dead.wall_cladding_udl_kn_per_m,
        # Imposed loads
        "w_imposed": imp,
        "imposed_area_kpa": imp.roof_imposed_kpa,
        "imposed_udl_kn_m": imp.roof_udl_kn_per_m,
        "imposed_clause": imp.clause,
        "imposed_category": imp.category,
        # ULS-1 combination
        "uls1_name": uls1.name,
        "gamma_G": gamma_G,
        "gamma_Q": gamma_Q,
        "uls_rafter_udl_kn_m": uls_raf_udl,
        "uls_col_udl_kn_m": uls_col_udl,
        "combo_clause": "SANS 10160-1:2011 Table 3",
        # Analysis forces
        "forces": forces,
        "eaves_moment_knm": abs(forces["eaves_L"].moment_knm),
        "eaves_shear_kn": abs(forces["eaves_L"].shear_kn),
        "eaves_axial_kn": abs(forces["eaves_L"].axial_kn),
        "apex_moment_knm": abs(forces["apex"].moment_knm),
        "apex_shear_kn": abs(forces["apex"].shear_kn),
        "apex_axial_kn": abs(forces["apex"].axial_kn),
        "base_shear_kn": abs(forces["col_base_L"].shear_kn),
        "base_axial_kn": abs(forces["col_base_L"].axial_kn),
        # Member capacities
        "member_workings": member_workings,
    }


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

    # Show-your-working data (FR-26)
    working = _compute_working(result)

    # Audit metadata (PRD FR-20)
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    fingerprint  = report_fingerprint(result)

    # Member checks for the main code-checks table (the connection/baseplate/footing
    # checks render in their own dedicated sections — Task 2.8 — to avoid duplication).
    member_checks = [
        c for c in result.checks if not c.name.startswith(_DETAIL_CHECK_PREFIXES)
    ]

    ctx: dict[str, Any] = {
        "generated_at": generated_at,   # full ISO-8601 UTC datetime
        "generated_date": generated_at, # backward-compat alias used in footer
        "report_fingerprint": fingerprint,
        "geom": geom,
        "dead": dead,
        "wind": wind,
        "base_fixity": result.frame_spec.base_fixity.value,
        "steel_grade": result.frame_spec.materials.steel_grade.value,
        "fy_mpa": fy_mpa,
        "sections": result.sections,
        "checks": result.checks,
        "member_checks": member_checks,
        "result_passed": result.passed,
        "governing_utilisation": result.governing_utilisation,
        # Last-mile structured results (Task 1.18) for dedicated report sections (Task 2.8)
        "connections": result.connections,
        "baseplate": result.baseplate,
        "footing": result.footing,
        # Characteristic wind actions per SANS 10160-3 (qp, net coefficients, member loads)
        "wind_actions": result.wind,
        "total_steel_tonnes": result.total_steel_tonnes,
        "foundation_allowable_bearing_kpa": result.frame_spec.foundation.allowable_bearing_kpa,
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
        "near_limit_threshold": NEAR_LIMIT_THRESHOLD,
        # Restraints (None if unrestrained)
        "restraints_rafter_m":  result.frame_spec.restraints.rafter_restraint_spacing_m,
        "restraints_column_m":  result.frame_spec.restraints.column_restraint_spacing_m,
        # Show-your-working (FR-26)
        **working,
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
        import weasyprint
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "WeasyPrint is required for PDF rendering. "
            "Install with: pip install weasyprint (requires Python 3.11 + pango/cairo on macOS). "
            "See docs/HANDOVER.md for environment setup."
        ) from exc

    html_string = render_html(result)
    pdf_bytes: bytes = weasyprint.HTML(string=html_string).write_pdf()
    return pdf_bytes
