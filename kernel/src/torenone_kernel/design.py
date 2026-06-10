"""Orchestrator — Task 1.12.

`design(spec)` runs the complete SANS 10162-1 portal-frame design pipeline:

  1. Loads: dead (SANS 10160-2) + imposed (SANS 10160-2) + combinations (SANS 10160-1)
  2. Iterative section sizing on ULS-1 (gravity dominant: 1.2G + 1.6Q):
     a. Compute dead loads with current trial sections
     b. Run first-order elastic portal-frame analysis (PyNite)
     c. Extract governing member forces at the knee joint
     d. Auto-size rafter + column (lightest SAISC section passing all cl. 13 checks)
     e. Repeat until sections converge (≤ 5 iterations)
  3. Sway sensitivity — SANS 10162-1 cl. 8.7 (U2 factor, notional-force approach)
  4. SLS vertical deflection — Annex D L/240 (beam-theory estimate — see warnings)
  5. Assemble DesignResult with all CheckResults, section choices, rules_version, warnings

OUT OF SCOPE (deferred — see warnings in result):
  - Wind load combinations (ULS-2/3, SLS-2): require horizontal portal loading which the
    current analysis model does not support. Engineer must check wind effects independently.
  - Effective length factors K ≠ 1.0: the orchestrator uses K=1.0 for both rafter and
    column (conservative lower bound for capacity). For sway frames, K > 1.0 may apply to
    columns. Engineer must verify per SANS 10162-1 cl. 8.6 or rational analysis.

All engineering constants are sourced from SANS 10162-1:2011 — see individual modules for
clause citations. All values traceable to the standard; PROVISIONAL items flagged in
SOURCES.md.
"""

from __future__ import annotations

import math
from typing import Optional

from torenone_kernel.analysis.plane_frame import PortalAnalysis
from torenone_kernel.analysis.sway_check import compute_sway_check
from torenone_kernel.checks.autosize import autosize_member, NoSectionFoundError
from torenone_kernel.checks.deflection import vertical_deflection_check
from torenone_kernel.checks.material import fy_mpa as _fy_mpa
from torenone_kernel.loads.combinations import (
    load_combinations,
    GAMMA_G_SLS_UNFAVOURABLE,
    GAMMA_Q_SLS,
)
from torenone_kernel.loads.dead import dead_loads
from torenone_kernel.loads.imposed import imposed_roof_loads
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import CheckResult, DesignResult, SectionChoice
from torenone_kernel.rules_version import as_dict as _rules_version
from torenone_kernel.sections.library import SectionLibrary
from torenone_kernel.sections.properties import SectionProperties

_K_EFFECTIVE = 1.0   # conservative lower bound — see module docstring (PROVISIONAL)
_MAX_ITERATIONS = 5  # convergence guard


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def design(spec: FrameSpec) -> DesignResult:
    """Run the full SANS 10162-1 portal-frame design pipeline for *spec*.

    Parameters
    ----------
    spec : FrameSpec — fully-validated, frozen frame + load description.

    Returns
    -------
    DesignResult — sections chosen, all checks with utilisations, rules_version, warnings.
    The result is deterministic: identical inputs → identical outputs (same library).
    """
    library = SectionLibrary.load_default()
    combos = {c.name.split()[0]: c for c in load_combinations(spec)}

    # Identify combinations needed
    uls1 = _combo_starting_with(combos, "ULS-1")
    sls1 = _combo_starting_with(combos, "SLS-1")

    imposed = imposed_roof_loads(spec)
    geom = spec.geometry

    # Derived geometry (all in mm)
    span_mm = geom.span_m * 1_000.0
    eaves_h_mm = geom.eaves_height_m * 1_000.0
    half_span_mm = span_mm / 2.0
    rafter_half_len_mm = math.hypot(
        half_span_mm,
        (geom.apex_height_m - geom.eaves_height_m) * 1_000.0,
    )
    pitch_rad = math.radians(geom.roof_pitch_deg)

    # ULS-1 partial factors
    gamma_G = uls1.factors["dead"]
    gamma_Q = uls1.factors.get("imposed", 0.0)

    # Effective lengths (K=1.0 — see module-level notes; PROVISIONAL)
    KL_col_mm = _K_EFFECTIVE * eaves_h_mm
    KL_raf_mm = _K_EFFECTIVE * rafter_half_len_mm

    # Unbraced lengths for LTB
    LTB_col_mm = (
        spec.restraints.column_restraint_spacing_m * 1_000.0
        if spec.restraints.column_restraint_spacing_m
        else eaves_h_mm
    )
    LTB_raf_mm = (
        spec.restraints.rafter_restraint_spacing_m * 1_000.0
        if spec.restraints.rafter_restraint_spacing_m
        else rafter_half_len_mm
    )

    # ------------------------------------------------------------------ #
    # Iterative sizing on ULS-1                                           #
    # ------------------------------------------------------------------ #
    # Start with the lightest section as the trial for self-weight.
    sections_ordered = library.by_increasing_mass()
    col_sec: SectionProperties = sections_ordered[0]
    raf_sec: SectionProperties = sections_ordered[0]

    for _iteration in range(_MAX_ITERATIONS):
        dead = dead_loads(spec, rafter=raf_sec, column=col_sec)

        fy_raf = _fy_mpa(spec.materials.steel_grade, raf_sec.flange_thickness_mm)
        fy_col = _fy_mpa(spec.materials.steel_grade, col_sec.flange_thickness_mm)

        # ULS-1 combined UDLs (kN/m = N/mm numerically)
        uls_rafter_udl = gamma_G * dead.rafter_udl_kn_per_m + gamma_Q * imposed.roof_udl_kn_per_m
        uls_col_axial_udl = gamma_G * (
            dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m
        )

        # First-order elastic analysis for ULS-1
        analysis = PortalAnalysis(spec, col_sec, raf_sec).run(
            uls1.name, uls_rafter_udl, uls_col_axial_udl
        )
        forces = {f.location: f for f in analysis.forces}

        # ---- Governing column forces (at eaves — top of column) ---- #
        # The knee joint (node EL) is where the column moment is maximum.
        # eaves_L gives forces in COL_L at x=eaves_height (the EL joint).
        col_mu_kn_m = abs(forces["eaves_L"].moment_knm)
        col_vu_kn   = abs(forces["eaves_L"].shear_kn)
        # Column axial = compressive reaction from the frame = approx. vertical
        # reaction at the base (change along column height from self-weight is small).
        col_cu_kn   = abs(forces["col_base_L"].axial_kn)

        # ---- Governing rafter forces (at eaves — start of rafter) ---- #
        # The rafter and column share the knee joint so M_knee is the same.
        raf_mu_kn_m = max(abs(forces["eaves_L"].moment_knm), abs(forces["apex"].moment_knm))
        raf_vu_kn   = max(abs(forces["eaves_L"].shear_kn),  abs(forces["apex"].shear_kn))
        # Rafter axial ≈ horizontal thrust H / cos(pitch).
        # H = horizontal reaction at pin base = shear in the column at the base.
        # For a vertical column with purely vertical loads:
        #   COL_L "Fy" shear = horizontal force component = H.
        H_kn = abs(forces["col_base_L"].shear_kn)
        raf_cu_kn = H_kn / math.cos(pitch_rad) if math.cos(pitch_rad) > 0 else H_kn

        # Auto-size
        raf_result = autosize_member(
            library, fy_raf,
            cu_kn=raf_cu_kn, vu_kn=raf_vu_kn, mu_knm=raf_mu_kn_m,
            KL_mm=KL_raf_mm, LTB_mm=LTB_raf_mm,
            member="rafter",
        )
        col_result = autosize_member(
            library, fy_col,
            cu_kn=col_cu_kn, vu_kn=col_vu_kn, mu_knm=col_mu_kn_m,
            KL_mm=KL_col_mm, LTB_mm=LTB_col_mm,
            member="column",
        )

        new_raf_sec = library.get(raf_result.section.designation)
        new_col_sec = library.get(col_result.section.designation)

        converged = (
            new_raf_sec.designation == raf_sec.designation
            and new_col_sec.designation == col_sec.designation
        )
        raf_sec = new_raf_sec
        col_sec = new_col_sec

        if converged:
            break

    # ------------------------------------------------------------------ #
    # Sway sensitivity check (SANS 10162-1 cl. 8.7)                      #
    # ------------------------------------------------------------------ #
    # Total factored vertical load on frame (ULS-1)
    total_gravity_kn = (
        uls_rafter_udl * geom.span_m                          # rafters
        + uls_col_axial_udl * geom.eaves_height_m * 2.0      # both columns
    )
    sway = compute_sway_check(
        spec, col_sec, raf_sec,
        total_factored_gravity_kn=total_gravity_kn,
        combination_name=uls1.name,
    )
    sway_check_result = CheckResult(
        name="Sway sensitivity U2 (cl. 8.7)",
        clause="SANS 10162-1:2011 cl. 8.7",
        utilisation=sway.U2 / 1.4,   # utilisation relative to sway-sensitive threshold
        passed=not sway.is_sway_sensitive,
        detail=f"U2={sway.U2:.3f}, θ={sway.stability_index:.4f}",
    )

    # ------------------------------------------------------------------ #
    # SLS vertical deflection (elastic FEA — Annex D L/240)             #
    # ------------------------------------------------------------------ #
    # Recompute dead loads with the FINAL strength-sized sections.
    dead_final = dead_loads(spec, rafter=raf_sec, column=col_sec)

    def _compute_sls_rafter_udl(raf: SectionProperties) -> tuple[float, float]:
        """Return (sls_rafter_udl, sls_col_axial_udl) for the given rafter."""
        d = dead_loads(spec, rafter=raf, column=col_sec)
        return (
            GAMMA_G_SLS_UNFAVOURABLE * d.rafter_udl_kn_per_m + GAMMA_Q_SLS * imposed.roof_udl_kn_per_m,
            GAMMA_G_SLS_UNFAVOURABLE * (d.column_self_weight_kn_per_m + d.wall_cladding_udl_kn_per_m),
        )

    def _apex_deflection_mm(raf: SectionProperties, sls_raf_udl: float, sls_col_udl: float) -> float:
        """Return abs(apex DY) from first-order SLS-1 analysis."""
        disp = PortalAnalysis(spec, col_sec, raf).node_displacements(
            sls1.name, sls_raf_udl, sls_col_udl
        )
        return abs(disp["AP"]["DY"])

    # If the strength-sized rafter fails deflection, advance through the library
    # lightest-first until deflection passes (deflection governs over strength for stiff
    # but relatively shallow sections). This ensures the lightest section satisfying BOTH
    # strength AND deflection is returned.
    sls_raf_udl, sls_col_udl = _compute_sls_rafter_udl(raf_sec)
    apex_delta_mm = _apex_deflection_mm(raf_sec, sls_raf_udl, sls_col_udl)
    deflection_limit_mm = span_mm / 240.0

    if apex_delta_mm > deflection_limit_mm:
        # Strength-sized rafter fails deflection — advance through heavier sections.
        # Require the candidate to satisfy BOTH deflection AND strength (slenderness can
        # cause a "heavier" section to still fail if its ry is too small for KL).
        for candidate in library.by_increasing_mass():
            if candidate.mass_per_metre_kg_m <= raf_sec.mass_per_metre_kg_m:
                continue   # skip sections no heavier than the strength-chosen section
            # Deflection check
            sls_raf_udl_c, sls_col_udl_c = _compute_sls_rafter_udl(candidate)
            delta_c = _apex_deflection_mm(candidate, sls_raf_udl_c, sls_col_udl_c)
            if delta_c > deflection_limit_mm:
                continue   # still fails deflection; try next
            # Strength re-check (slenderness may exclude the candidate even if it's heavier)
            fy_raf_final = _fy_mpa(spec.materials.steel_grade, candidate.flange_thickness_mm)
            try:
                new_raf_result = autosize_member(
                    SectionLibrary([candidate]),
                    fy_raf_final,
                    cu_kn=raf_cu_kn, vu_kn=raf_vu_kn, mu_knm=raf_mu_kn_m,
                    KL_mm=KL_raf_mm, LTB_mm=LTB_raf_mm,
                    member="rafter",
                )
            except NoSectionFoundError:
                continue   # candidate fails slenderness or a strength check — skip
            # Both deflection AND strength pass — accept this section
            raf_sec = candidate
            raf_result = new_raf_result
            sls_raf_udl = sls_raf_udl_c
            apex_delta_mm = delta_c
            break
        # If no heavier section satisfies both constraints, deflection check will report
        # passed=False (apex_delta_mm retains the failing value from the loop above).

    vertical_deflection = vertical_deflection_check(
        delta_mm=apex_delta_mm,
        span_mm=span_mm,
        limit_fraction=240,
    )

    # ------------------------------------------------------------------ #
    # Assemble result                                                      #
    # ------------------------------------------------------------------ #
    all_checks: list[CheckResult] = (
        list(raf_result.checks)
        + list(col_result.checks)
        + [sway_check_result, vertical_deflection]
    )

    sections = [
        SectionChoice(member="rafter", designation=raf_sec.designation),
        SectionChoice(member="column", designation=col_sec.designation),
    ]

    warnings: list[str] = [
        "Effective length factors K=1.0 assumed for both rafter and column (PROVISIONAL). "
        "For sway portal frames with pinned bases, cl. 8.6 or rational analysis may require "
        "K > 1.0 for columns. Engineer must verify.",
        "ULS wind combinations (ULS-2, ULS-3) and SLS wind sway (SLS-2) NOT checked in this "
        "run — wind analysis requires horizontal frame loading which the current model does "
        "not include. Engineer must check wind effects independently.",
        "Vertical deflection computed by first-order linear elastic FEA (PyNite) under "
        "SLS-1 gravity combination. Second-order deflection amplification not included; "
        "for sway-sensitive frames engineer should verify amplified deflections.",
    ]
    if sway.is_sway_sensitive:
        warnings.append(
            f"Frame is sway-sensitive (U2={sway.U2:.3f} > 1.4). Second-order effects must be "
            "amplified. Consider increasing section stiffness or bracing the frame."
        )

    return DesignResult(
        frame_spec=spec,
        sections=sections,
        checks=all_checks,
        rules_version=_rules_version(),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _combo_starting_with(
    combos: dict[str, object], prefix: str
) -> object:  # type: ignore[return]
    """Return the first LoadCombination whose name starts with *prefix*."""
    for name, combo in combos.items():
        if name.startswith(prefix):
            return combo
    raise KeyError(f"No load combination starting with {prefix!r} in: {list(combos)}")
