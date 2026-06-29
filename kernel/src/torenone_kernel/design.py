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

WIND (PROVISIONAL — pending registered-engineer validation of the wind-on-frame method):
  - ULS-2/3 wind combinations: members are CHECKED under transverse wind and the results
    reported as ADVISORY (informational, non-gating) — they do NOT gate passed/governing,
    because the wind method is provisional and members are sized on gravity only. Auto-sizing
    for wind is available via `design(autosize_for_wind=True)` but is OFF by default. Once the
    method is validated, flip the wind checks to gating + auto-sizing on, together.
  - SLS-2 wind sway (eaves lateral drift vs Annex D H/400): also reported as an ADVISORY
    (informational, non-gating) check — Annex D is informative and the model is PROVISIONAL.

OUT OF SCOPE (deferred — see warnings in result):
  - Effective length factors K ≠ 1.0: the orchestrator uses K=1.0 for both rafter and
    column (conservative lower bound for capacity). For sway frames, K > 1.0 may apply to
    columns. Engineer must verify per SANS 10162-1 cl. 8.6 or rational analysis.

All engineering constants are sourced from SANS 10162-1:2011 — see individual modules for
clause citations. All values traceable to the standard; PROVISIONAL items flagged in
SOURCES.md.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from typing import NamedTuple

from torenone_kernel.analysis.diagram_data import compute_frame_diagram
from torenone_kernel.analysis.plane_frame import PortalAnalysis
from torenone_kernel.analysis.sway_check import FrameUnstableError, compute_sway_check
from torenone_kernel.checks.autosize import (
    NoSectionFoundError,
    SectionIneligibleError,
    autosize_member,
    run_member_checks,
)
from torenone_kernel.checks.deflection import (
    horizontal_sway_check,
    vertical_deflection_check,
)
from torenone_kernel.codes import DEFAULT_CODE, DesignCode
from torenone_kernel.loads.combinations import (
    GAMMA_G_SLS_UNFAVOURABLE,
    GAMMA_Q_SLS,
)
from torenone_kernel.loads.dead import dead_loads
from torenone_kernel.loads.imposed import imposed_roof_loads
from torenone_kernel.loads.wind_loads import wind_loads
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import (
    AutosizeResult,
    BaseplateDesignResult,
    CheckResult,
    ConnectionDesignResult,
    DeadLoadResult,
    DesignResult,
    LoadCombination,
    MemberForces,
    PadFootingDesignResult,
    SectionChoice,
)
from torenone_kernel.sections.library import SectionLibrary
from torenone_kernel.sections.properties import SectionProperties

_K_EFFECTIVE = 1.0   # conservative lower bound — see module docstring (PROVISIONAL)
_MAX_ITERATIONS = 5  # convergence guard

# Default indicative cost rate for South African fabricated structural steel.
# R20 000/tonne = R20/kg; market rates R18 000–R25 000/tonne (2025).
# PROVISIONAL — verify with fabricator before using for cost estimates (SOURCES.md).
DEFAULT_COST_RATE_ZAR_PER_KG: float = 20.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class _WindMemberForces(NamedTuple):
    """Worst per-member factored demands from a wind-combination analysis (all kN / kN·m)."""

    col_cu: float
    col_vu: float
    col_mu: float
    raf_cu: float
    raf_vu: float
    raf_mu: float

    def enveloped_with(self, other: _WindMemberForces) -> _WindMemberForces:
        """Component-wise max of two demand sets (conservative envelope)."""
        return _WindMemberForces(*(max(a, b) for a, b in zip(self, other, strict=True)))


def _extract_wind_member_forces(forces: dict[str, MemberForces]) -> _WindMemberForces:
    """Governing column + rafter demands from one wind-combination force set.

    Axial treated as compression (abs) — mirrors the PROVISIONAL wind-on-frame model used
    by both the wind CHECK and (when enabled) the wind AUTO-SIZE path, so they stay
    consistent.
    """
    f = forces
    col_mu = max(abs(f["eaves_L"].moment_knm), abs(f["eaves_R"].moment_knm))
    col_vu = max(abs(x.shear_kn) for x in f.values())
    col_cu = max(abs(f["col_base_L"].axial_kn), abs(f["col_base_R"].axial_kn))
    raf_mu = max(
        abs(f["eaves_L"].moment_knm), abs(f["eaves_R"].moment_knm), abs(f["apex"].moment_knm)
    )
    raf_vu = max(abs(f["apex"].shear_kn), abs(f["eaves_L"].shear_kn))
    raf_cu = abs(f["apex"].axial_kn)
    return _WindMemberForces(col_cu, col_vu, col_mu, raf_cu, raf_vu, raf_mu)


def _iter_wind_analyses(
    spec: FrameSpec,
    *,
    col_sec: SectionProperties,
    raf_sec: SectionProperties,
    dead: DeadLoadResult,
    combos: dict[str, LoadCombination],
    keys: tuple[str, ...] = ("ULS-2", "ULS-3"),
) -> Iterator[tuple[str, LoadCombination, dict[str, MemberForces]]]:
    """Yield (key, combo, forces-by-location) for every wind load case of each combination.

    Single source of the factored-load wind analysis used by the wind CHECK and the wind
    AUTO-SIZE envelope. PROVISIONAL — see `PortalAnalysis.run_wind_combination`.
    """
    wind = wind_loads(spec)
    col_dead = dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m
    for key in keys:
        combo = combos.get(key)
        if combo is None:
            continue
        g_g = combo.factors.get("dead", 1.0)
        g_w = combo.factors.get("wind", 1.0)
        for case in wind.cases:
            analysis = PortalAnalysis(spec, col_sec, raf_sec).run_wind_combination(
                combo.name,
                rafter_dead_udl_kn_per_m=g_g * dead.rafter_udl_kn_per_m,
                column_dead_udl_kn_per_m=g_g * col_dead,
                windward_column_udl_kn_per_m=g_w * case.windward_column_udl_kn_per_m,
                leeward_column_udl_kn_per_m=g_w * case.leeward_column_udl_kn_per_m,
                windward_rafter_udl_kn_per_m=g_w * case.windward_rafter_udl_kn_per_m,
                leeward_rafter_udl_kn_per_m=g_w * case.leeward_rafter_udl_kn_per_m,
            )
            yield key, combo, {x.location: x for x in analysis.forces}


def _worst_wind_demands(
    spec: FrameSpec,
    *,
    col_sec: SectionProperties,
    raf_sec: SectionProperties,
    dead: DeadLoadResult,
    combos: dict[str, LoadCombination],
) -> _WindMemberForces:
    """Component-wise envelope of member demands over all wind cases (ULS-2/3).

    Used ONLY when `design(autosize_for_wind=True)` — sizes members for the worst wind
    demand alongside gravity. PROVISIONAL: this is gated OFF by default pending
    registered-engineer validation of the wind-on-frame method.
    """
    envelope = _WindMemberForces(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    for _key, _combo, forces in _iter_wind_analyses(
        spec, col_sec=col_sec, raf_sec=raf_sec, dead=dead, combos=combos
    ):
        envelope = envelope.enveloped_with(_extract_wind_member_forces(forces))
    return envelope


def _wind_combination_checks(
    spec: FrameSpec,
    *,
    col_sec: SectionProperties,
    raf_sec: SectionProperties,
    dead: DeadLoadResult,
    combos: dict[str, LoadCombination],
    fy_col: float,
    fy_raf: float,
    kl_col_mm: float,
    ltb_col_mm: float,
    kl_raf_mm: float,
    ltb_raf_mm: float,
) -> list[CheckResult]:
    """Check the members under the wind combinations ULS-2/3 (Part B).

    For each wind combination, the worst of the wind load cases governs. The worst-case
    member checks are reported (suffixed `[ULS-2 wind]` / `[ULS-3 wind]`) with their
    utilisations, so a wind-governed inadequacy is surfaced for the engineer.

    **Reported as INFORMATIONAL (advisory-only, non-gating)** — they do NOT gate the
    design's `passed` / `governing_utilisation`, because the wind-on-frame analysis is
    PROVISIONAL: mechanically validated (equilibrium, uplift, asymmetry) but its SANS
    engineering correctness (sign conventions + governing case) is pending registered-engineer
    validation, and members are sized on gravity only (autosize_for_wind off by default).
    Once the method is validated, flip these to gating together with auto-sizing for wind.
    """
    best_per_key: dict[str, tuple[float, list[CheckResult]]] = {}
    for key, _combo, forces in _iter_wind_analyses(
        spec, col_sec=col_sec, raf_sec=raf_sec, dead=dead, combos=combos
    ):
        d = _extract_wind_member_forces(forces)
        try:
            checks = run_member_checks(
                col_sec, fy_col, d.col_cu, d.col_vu, d.col_mu, kl_col_mm, ltb_col_mm,
                member="column",
            ) + run_member_checks(
                raf_sec, fy_raf, d.raf_cu, d.raf_vu, d.raf_mu, kl_raf_mm, ltb_raf_mm,
                member="rafter",
            )
        except SectionIneligibleError:
            continue
        util = max((c.utilisation for c in checks), default=0.0)
        prev = best_per_key.get(key)
        if prev is None or util > prev[0]:
            best_per_key[key] = (util, checks)

    out: list[CheckResult] = []
    for key in ("ULS-2", "ULS-3"):
        entry = best_per_key.get(key)
        if entry is None:
            continue
        combo = combos[key]
        for c in entry[1]:
            detail = (
                f"PROVISIONAL advisory (non-gating). Wind-combination check ({combo.name}). "
                f"{c.detail or ''}"
            ).strip()
            out.append(
                CheckResult(
                    name=f"{c.name} [{key} wind]",
                    clause=c.clause,
                    utilisation=c.utilisation,
                    passed=c.passed,
                    informational=True,
                    detail=detail,
                )
            )
    return out


def _wind_sway_check(
    spec: FrameSpec,
    *,
    col_sec: SectionProperties,
    raf_sec: SectionProperties,
    dead: DeadLoadResult,
    combos: dict[str, LoadCombination],
) -> CheckResult | None:
    """SLS-2 eaves wind-sway (lateral drift) check — Annex D Table D.1 (H/400).

    Worst lateral eaves drift over all wind cases under the SLS-2 (characteristic
    dead + wind) combination, compared to H/400. Returns ``None`` if no SLS-2 combination
    exists.

    **Reported as INFORMATIONAL (advisory-only)** — it does NOT gate the design's
    `passed` / `governing_utilisation`, because (a) Annex D is informative (non-normative)
    and portal frames are often assessed against a relaxed practice limit (e.g. H/150) that
    requires engineer sign-off, and (b) the wind-on-frame model is PROVISIONAL. The drift +
    utilisation are surfaced so the engineer can judge serviceability.
    """
    combo = combos.get("SLS-2")
    if combo is None:
        return None
    wind = wind_loads(spec)
    col_dead = dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m
    g_g = combo.factors.get("dead", 1.0)
    g_w = combo.factors.get("wind", 1.0)
    eaves_h_mm = spec.geometry.eaves_height_m * 1_000.0

    worst_drift_mm = 0.0
    for case in wind.cases:
        disp = PortalAnalysis(spec, col_sec, raf_sec).wind_combination_displacements(
            rafter_dead_udl_kn_per_m=g_g * dead.rafter_udl_kn_per_m,
            column_dead_udl_kn_per_m=g_g * col_dead,
            windward_column_udl_kn_per_m=g_w * case.windward_column_udl_kn_per_m,
            leeward_column_udl_kn_per_m=g_w * case.leeward_column_udl_kn_per_m,
            windward_rafter_udl_kn_per_m=g_w * case.windward_rafter_udl_kn_per_m,
            leeward_rafter_udl_kn_per_m=g_w * case.leeward_rafter_udl_kn_per_m,
        )
        worst_drift_mm = max(
            worst_drift_mm, abs(disp["EL"]["DX"]), abs(disp["ER"]["DX"])
        )

    base = horizontal_sway_check(worst_drift_mm, eaves_h_mm)
    limit_mm = eaves_h_mm / 400.0
    return CheckResult(
        name=f"{base.name} [SLS-2 wind]",
        clause=base.clause,
        utilisation=base.utilisation,
        passed=base.passed,
        informational=True,
        detail=(
            f"PROVISIONAL advisory (non-gating). Worst eaves drift "
            f"{worst_drift_mm:.1f} mm vs H/400 = {limit_mm:.1f} mm "
            f"(practice limit H/150 = {eaves_h_mm / 150.0:.1f} mm). Serviceability only; "
            "wind-on-frame model pending registered-engineer validation."
        ),
    )


def design(
    spec: FrameSpec,
    cost_rate_zar_per_kg: float = DEFAULT_COST_RATE_ZAR_PER_KG,
    *,
    autosize_for_wind: bool = False,
    code: DesignCode = DEFAULT_CODE,
) -> DesignResult:
    """Run the full SANS 10162-1 portal-frame design pipeline for *spec*.

    Parameters
    ----------
    spec : FrameSpec — fully-validated, frozen frame + load description.
    cost_rate_zar_per_kg : indicative steel cost rate (PROVISIONAL default).
    autosize_for_wind : if True, members are auto-sized to satisfy the wind combinations
        ULS-2/3 (component-wise demand envelope) IN ADDITION to gravity (ULS-1). **Defaults
        to False** — gravity sizes the members and wind is only CHECKED (reported, gating) —
        because the wind-on-frame method is PROVISIONAL and must be validated by a
        registered engineer before it is trusted to drive member sizes. Flip to True only
        after that validation (the wind checks then ride along at ≤ 1.0).

    Returns
    -------
    DesignResult — sections chosen, all checks with utilisations, rules_version, warnings.
    The result is deterministic: identical inputs → identical outputs (same library).
    """
    library = code.section_library()
    combos = {c.name.split()[0]: c for c in code.load_combinations(spec)}

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

        fy_raf = code.material_fy(spec.materials.steel_grade, raf_sec.flange_thickness_mm)
        fy_col = code.material_fy(spec.materials.steel_grade, col_sec.flange_thickness_mm)

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

        # ---- Optionally envelope wind demands (ULS-2/3) into the sizing ---- #
        # PROVISIONAL + OFF by default — see the `autosize_for_wind` docstring. When on,
        # each member is sized for the component-wise worst of gravity AND wind, so the
        # resulting sections satisfy both (the wind checks then report ≤ 1.0).
        if autosize_for_wind:
            wd = _worst_wind_demands(
                spec, col_sec=col_sec, raf_sec=raf_sec, dead=dead, combos=combos
            )
            col_cu_kn = max(col_cu_kn, wd.col_cu)
            col_vu_kn = max(col_vu_kn, wd.col_vu)
            col_mu_kn_m = max(col_mu_kn_m, wd.col_mu)
            raf_cu_kn = max(raf_cu_kn, wd.raf_cu)
            raf_vu_kn = max(raf_vu_kn, wd.raf_vu)
            raf_mu_kn_m = max(raf_mu_kn_m, wd.raf_mu)

        # Auto-size
        raf_result = autosize_member(
            library, fy_raf,
            cu_kn=raf_cu_kn, vu_kn=raf_vu_kn, mu_knm=raf_mu_kn_m,
            KL_mm=KL_raf_mm, LTB_mm=LTB_raf_mm,
            member="rafter", code=code,
        )
        col_result = autosize_member(
            library, fy_col,
            cu_kn=col_cu_kn, vu_kn=col_vu_kn, mu_knm=col_mu_kn_m,
            KL_mm=KL_col_mm, LTB_mm=LTB_col_mm,
            member="column", code=code,
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
    # The strength search optimises for weight and ignores stiffness, so a wide-span roof can be
    # strong enough yet sag past L/240. Apex deflection falls as EITHER the rafter OR the columns
    # get stiffer, so we look for the lightest (rafter, column) pair that satisfies BOTH the
    # deflection limit and every strength check. Deepening the rafter is the bigger lever for sag,
    # so we try that first (cheap, handles most frames) and escalate the column only when even the
    # stiffest rafter can't get there with the strength-sized column.
    deflection_limit_mm = span_mm / code.deflection_limit_fraction()

    def _apex_deflection_mm(raf: SectionProperties, col: SectionProperties) -> float:
        """Return abs(apex vertical deflection, mm) from first-order SLS-1 analysis for (raf, col)."""
        d = dead_loads(spec, rafter=raf, column=col)
        sls_raf_udl = GAMMA_G_SLS_UNFAVOURABLE * d.rafter_udl_kn_per_m + GAMMA_Q_SLS * imposed.roof_udl_kn_per_m
        sls_col_udl = GAMMA_G_SLS_UNFAVOURABLE * (
            d.column_self_weight_kn_per_m + d.wall_cladding_udl_kn_per_m
        )
        disp = PortalAnalysis(spec, col, raf).node_displacements(sls1.name, sls_raf_udl, sls_col_udl)
        return abs(disp["AP"]["DY"])

    def _strength_result(
        section: SectionProperties, member: str,
        cu_kn: float, vu_kn: float, mu_knm: float, kl_mm: float, ltb_mm: float,
    ) -> AutosizeResult | None:
        """Strength check for a single section; None if it fails any strength check / slenderness."""
        try:
            return autosize_member(
                SectionLibrary([section]),
                code.material_fy(spec.materials.steel_grade, section.flange_thickness_mm),
                cu_kn=cu_kn, vu_kn=vu_kn, mu_knm=mu_knm, KL_mm=kl_mm, LTB_mm=ltb_mm,
                member=member, code=code,
            )
        except NoSectionFoundError:
            return None

    def _lightest_rafter_for(col: SectionProperties) -> tuple[SectionProperties, AutosizeResult] | None:
        """Lightest rafter (≥ the strength-sized rafter) passing deflection (with `col`) + strength."""
        for cand in library.by_increasing_mass():
            if cand.mass_per_metre_kg_m < raf_sec.mass_per_metre_kg_m:
                continue
            if _apex_deflection_mm(cand, col) > deflection_limit_mm:
                continue
            res = _strength_result(
                cand, "rafter", raf_cu_kn, raf_vu_kn, raf_mu_kn_m, KL_raf_mm, LTB_raf_mm
            )
            if res is not None:
                return cand, res
        return None

    apex_delta_mm = _apex_deflection_mm(raf_sec, col_sec)
    if apex_delta_mm > deflection_limit_mm:
        pick = _lightest_rafter_for(col_sec)
        if pick is not None:
            raf_sec, raf_result = pick
        else:
            # Even the stiffest rafter can't satisfy deflection with this column — escalate the
            # column (lightest-first) and re-search the rafter for each, taking the first feasible.
            for col_cand in library.by_increasing_mass():
                if col_cand.mass_per_metre_kg_m <= col_sec.mass_per_metre_kg_m:
                    continue
                if _strength_result(
                    col_cand, "column", col_cu_kn, col_vu_kn, col_mu_kn_m, KL_col_mm, LTB_col_mm
                ) is None:
                    continue
                pick = _lightest_rafter_for(col_cand)
                if pick is not None:
                    col_sec = col_cand
                    col_result = _strength_result(
                        col_cand, "column", col_cu_kn, col_vu_kn, col_mu_kn_m, KL_col_mm, LTB_col_mm
                    )  # type: ignore[assignment]  # not None — checked above
                    raf_sec, raf_result = pick
                    break
        # Recompute the final apex deflection for whatever (rafter, column) we settled on; if no
        # feasible pair was found the sections are unchanged and the check below reports the failure.
        apex_delta_mm = _apex_deflection_mm(raf_sec, col_sec)

    vertical_deflection = vertical_deflection_check(
        delta_mm=apex_delta_mm,
        span_mm=span_mm,
        limit_fraction=code.deflection_limit_fraction(),
    )

    # ------------------------------------------------------------------ #
    # The "last mile" — connections, baseplate, footing (final sections)  #
    # ------------------------------------------------------------------ #
    connections, baseplate, footing = _design_last_mile(spec, raf_sec, col_sec, code=code)

    # ------------------------------------------------------------------ #
    # Assemble result                                                      #
    # ------------------------------------------------------------------ #
    all_checks: list[CheckResult] = (
        list(raf_result.checks)
        + list(col_result.checks)
        + [sway_check_result, vertical_deflection]
        + _last_mile_checks(connections, baseplate, footing)
    )
    # Wind combinations ULS-2/3 — check members under wind (Part B; gating).
    all_checks += _wind_combination_checks(
        spec,
        col_sec=col_sec,
        raf_sec=raf_sec,
        dead=dead,
        combos=combos,
        fy_col=fy_col,
        fy_raf=fy_raf,
        kl_col_mm=KL_col_mm,
        ltb_col_mm=LTB_col_mm,
        kl_raf_mm=KL_raf_mm,
        ltb_raf_mm=LTB_raf_mm,
    )
    # SLS-2 wind sway (eaves lateral drift) — advisory-only (informational, non-gating).
    sway_drift_check = _wind_sway_check(
        spec, col_sec=col_sec, raf_sec=raf_sec, dead=dead, combos=combos
    )
    if sway_drift_check is not None:
        all_checks.append(sway_drift_check)

    sections = [
        SectionChoice(member="rafter", designation=raf_sec.designation),
        SectionChoice(member="column", designation=col_sec.designation),
    ]

    if autosize_for_wind:
        wind_sizing_note = (
            "Members are auto-sized for the envelope of gravity (ULS-1) AND wind (ULS-2/3) "
            "demands (autosize_for_wind=True), so the wind checks pass. The wind checks are "
            "still reported as ADVISORY (non-gating) until the wind-on-frame method is "
            "validated by a registered engineer."
        )
    else:
        wind_sizing_note = (
            "Members are auto-sized on gravity (ULS-1) only; the ULS-2/3 wind checks are "
            "reported as ADVISORY (informational, non-gating) with their utilisations — they "
            "do NOT fail the design — because the wind-on-frame method is PROVISIONAL "
            "(mechanically validated, but sign conventions + governing case pending "
            "registered-engineer validation). Once validated, the wind checks become gating "
            "together with auto-sizing for wind."
        )
    warnings: list[str] = [
        "Effective length factors K=1.0 assumed for both rafter and column (PROVISIONAL). "
        "For sway portal frames with pinned bases, cl. 8.6 or rational analysis may require "
        "K > 1.0 for columns. Engineer must verify.",
        "Characteristic wind actions (qp, net pressure coefficients, member line loads) are "
        "computed per SANS 10160-3, and the members are CHECKED under the wind combinations "
        "ULS-2 and ULS-3 (results suffixed '[ULS-2 wind]' / '[ULS-3 wind]'). " + wind_sizing_note,
        "SLS-2 wind sway (eaves lateral drift) is checked against Annex D H/400 and reported "
        "as an ADVISORY (informational, non-gating) result — Annex D is informative and the "
        "wind-on-frame model is PROVISIONAL. The engineer must judge serviceability sway.",
        "Vertical deflection computed by first-order linear elastic FEA (PyNite) under "
        "SLS-1 gravity combination. Second-order deflection amplification not included; "
        "for sway-sensitive frames engineer should verify amplified deflections.",
    ]
    if sway.is_sway_sensitive:
        warnings.append(
            f"Frame is sway-sensitive (U2={sway.U2:.3f} > 1.4). Second-order effects must be "
            "amplified. Consider increasing section stiffness or bracing the frame."
        )

    if footing is None and spec.foundation.allowable_bearing_kpa is None:
        warnings.append(
            "Pad footing NOT designed — no allowable bearing pressure supplied "
            "(spec.foundation.allowable_bearing_kpa). Provide the site value to "
            "complete the foundation design."
        )

    mass_kg = _steel_mass_kg(spec, raf_sec, col_sec)
    return DesignResult(
        frame_spec=spec,
        sections=sections,
        checks=all_checks,
        rules_version=code.rules_version(),
        warnings=tuple(warnings),
        total_steel_mass_kg=mass_kg,
        indicative_cost_zar=mass_kg * cost_rate_zar_per_kg,
        connections=connections,
        baseplate=baseplate,
        footing=footing,
        wind=wind_loads(spec),
        diagram=compute_frame_diagram(spec, raf_sec, col_sec),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def check(
    spec: FrameSpec,
    sections: list[SectionChoice],
    cost_rate_zar_per_kg: float = DEFAULT_COST_RATE_ZAR_PER_KG,
    *,
    code: DesignCode = DEFAULT_CODE,
) -> DesignResult:
    """Check engineer-supplied sections against SANS 10162-1:2011 without auto-sizing.

    This is the "check mode" variant of the kernel (PRD FR-24): the engineer specifies
    the section designations and the kernel runs all SANS 10162-1 strength checks,
    sway sensitivity, and SLS vertical deflection, reporting utilisations for every check.

    Parameters
    ----------
    spec     : FrameSpec — geometry + load context.
    sections : list of SectionChoice — must include a 'rafter' and a 'column' entry.
               Each designation is looked up in the default SAISC library.
    cost_rate_zar_per_kg : fabrication cost rate (ZAR/kg); default R20/kg (PROVISIONAL).

    Returns
    -------
    DesignResult — all checks with utilisations, chosen sections echoed back,
    total_steel_mass_kg, indicative_cost_zar, rules_version, warnings.
    The result may have passed=False if the supplied sections fail any check.

    Raises
    ------
    KeyError   : if a designation is not in the SAISC library.
    ValueError : if 'rafter' or 'column' member is not in sections.
    """
    library = code.section_library()

    # Resolve SectionChoice → SectionProperties
    sec_map: dict[str, SectionProperties] = {}
    for sc in sections:
        sec_map[sc.member] = library.get(sc.designation)

    if "rafter" not in sec_map:
        raise ValueError("sections must include a 'rafter' entry")
    if "column" not in sec_map:
        raise ValueError("sections must include a 'column' entry")

    raf_sec = sec_map["rafter"]
    col_sec = sec_map["column"]

    combos = {c.name.split()[0]: c for c in code.load_combinations(spec)}
    uls1 = _combo_starting_with(combos, "ULS-1")
    sls1 = _combo_starting_with(combos, "SLS-1")

    imposed = imposed_roof_loads(spec)
    geom = spec.geometry
    span_mm = geom.span_m * 1_000.0
    eaves_h_mm = geom.eaves_height_m * 1_000.0
    rafter_half_len_mm = math.hypot(
        span_mm / 2.0,
        (geom.apex_height_m - geom.eaves_height_m) * 1_000.0,
    )
    pitch_rad = math.radians(geom.roof_pitch_deg)

    gamma_G = uls1.factors["dead"]
    gamma_Q = uls1.factors.get("imposed", 0.0)

    KL_col_mm = _K_EFFECTIVE * eaves_h_mm
    KL_raf_mm = _K_EFFECTIVE * rafter_half_len_mm
    LTB_col_mm = (
        spec.restraints.column_restraint_spacing_m * 1_000.0
        if spec.restraints.column_restraint_spacing_m else eaves_h_mm
    )
    LTB_raf_mm = (
        spec.restraints.rafter_restraint_spacing_m * 1_000.0
        if spec.restraints.rafter_restraint_spacing_m else rafter_half_len_mm
    )

    # ---- Analysis (ULS-1) ----
    dead = dead_loads(spec, rafter=raf_sec, column=col_sec)
    fy_raf = code.material_fy(spec.materials.steel_grade, raf_sec.flange_thickness_mm)
    fy_col = code.material_fy(spec.materials.steel_grade, col_sec.flange_thickness_mm)

    uls_rafter_udl = gamma_G * dead.rafter_udl_kn_per_m + gamma_Q * imposed.roof_udl_kn_per_m
    uls_col_axial_udl = gamma_G * (
        dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m
    )

    analysis = PortalAnalysis(spec, col_sec, raf_sec).run(
        uls1.name, uls_rafter_udl, uls_col_axial_udl
    )
    forces = {f.location: f for f in analysis.forces}

    raf_mu  = max(abs(forces["eaves_L"].moment_knm), abs(forces["apex"].moment_knm))
    raf_vu  = max(abs(forces["eaves_L"].shear_kn),  abs(forces["apex"].shear_kn))
    H_kn    = abs(forces["col_base_L"].shear_kn)
    raf_cu  = H_kn / math.cos(pitch_rad) if math.cos(pitch_rad) > 0 else H_kn
    col_mu  = abs(forces["eaves_L"].moment_knm)
    col_vu  = abs(forces["eaves_L"].shear_kn)
    col_cu  = abs(forces["col_base_L"].axial_kn)

    # ---- Member strength checks ----
    raf_checks = _run_checks_safe(raf_sec, fy_raf, raf_cu, raf_vu, raf_mu,
                                   KL_raf_mm, LTB_raf_mm, member="rafter", code=code)
    col_checks = _run_checks_safe(col_sec, fy_col, col_cu, col_vu, col_mu,
                                   KL_col_mm, LTB_col_mm, member="column", code=code)

    # ---- Sway sensitivity ----
    total_gravity_kn = (
        uls_rafter_udl * geom.span_m
        + uls_col_axial_udl * geom.eaves_height_m * 2.0
    )
    _sway_sensitive = False
    try:
        sway = compute_sway_check(spec, col_sec, raf_sec, total_gravity_kn, uls1.name)
        _sway_sensitive = sway.is_sway_sensitive
        sway_check = CheckResult(
            name="Sway sensitivity U2 (cl. 8.7)",
            clause="SANS 10162-1:2011 cl. 8.7",
            utilisation=sway.U2 / 1.4,
            passed=not sway.is_sway_sensitive,
            detail=f"U2={sway.U2:.3f}, θ={sway.stability_index:.4f}",
        )
    except FrameUnstableError as exc:
        sway_check = CheckResult(
            name="Sway sensitivity U2 (cl. 8.7)",
            clause="SANS 10162-1:2011 cl. 8.7",
            utilisation=float("inf"),
            passed=False,
            detail=f"Frame geometrically unstable (θ ≥ 1.0): {exc}",
        )

    # ---- SLS vertical deflection ----
    sls_rafter_udl = (
        GAMMA_G_SLS_UNFAVOURABLE * dead.rafter_udl_kn_per_m
        + GAMMA_Q_SLS * imposed.roof_udl_kn_per_m
    )
    sls_col_udl = GAMMA_G_SLS_UNFAVOURABLE * (
        dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m
    )
    sls_disp = PortalAnalysis(spec, col_sec, raf_sec).node_displacements(
        sls1.name, sls_rafter_udl, sls_col_udl
    )
    deflection_check = vertical_deflection_check(
        delta_mm=abs(sls_disp["AP"]["DY"]),
        span_mm=span_mm,
        limit_fraction=code.deflection_limit_fraction(),
    )

    # ---- The "last mile" (connections, baseplate, footing) on supplied sections ----
    connections, baseplate, footing = _design_last_mile(spec, raf_sec, col_sec, code=code)

    # ---- Assemble ----
    all_checks: list[CheckResult] = (
        raf_checks + col_checks + [sway_check, deflection_check]
        + _last_mile_checks(connections, baseplate, footing)
    )
    # Wind combinations ULS-2/3 — check the supplied members under wind (Part B; gating).
    all_checks += _wind_combination_checks(
        spec,
        col_sec=col_sec,
        raf_sec=raf_sec,
        dead=dead,
        combos=combos,
        fy_col=fy_col,
        fy_raf=fy_raf,
        kl_col_mm=KL_col_mm,
        ltb_col_mm=LTB_col_mm,
        kl_raf_mm=KL_raf_mm,
        ltb_raf_mm=LTB_raf_mm,
    )
    # SLS-2 wind sway (eaves lateral drift) — advisory-only (informational, non-gating).
    sway_drift_check = _wind_sway_check(
        spec, col_sec=col_sec, raf_sec=raf_sec, dead=dead, combos=combos
    )
    if sway_drift_check is not None:
        all_checks.append(sway_drift_check)

    section_choices = [
        SectionChoice(member="rafter", designation=raf_sec.designation),
        SectionChoice(member="column", designation=col_sec.designation),
    ]
    warnings: list[str] = [
        "check() mode: sections were supplied by the engineer — no auto-sizing performed.",
        "Effective length factors K=1.0 assumed (PROVISIONAL). Engineer must verify per "
        "SANS 10162-1 cl. 8.6 for sway frames.",
        "Characteristic wind actions (qp, net pressure coefficients, member line loads) are "
        "computed per SANS 10160-3, and the supplied members are CHECKED under the wind "
        "combinations ULS-2/3 (results suffixed '[ULS-2 wind]' / '[ULS-3 wind]'), reported as "
        "ADVISORY (informational, non-gating) — they do NOT fail the result. PROVISIONAL: the "
        "wind-on-frame analysis is mechanically validated but its sign conventions + governing "
        "case need registered-engineer validation before the wind checks become gating.",
        "SLS-2 wind sway (eaves lateral drift) is checked against Annex D H/400 and reported "
        "as an ADVISORY (informational, non-gating) result — Annex D is informative and the "
        "wind-on-frame model is PROVISIONAL. The engineer must judge serviceability sway.",
    ]
    if _sway_sensitive:
        warnings.append(
            "Frame is sway-sensitive (U2 > 1.4). Second-order effects apply."
        )
    if footing is None and spec.foundation.allowable_bearing_kpa is None:
        warnings.append(
            "Pad footing NOT designed — no allowable bearing pressure supplied "
            "(spec.foundation.allowable_bearing_kpa)."
        )

    mass_kg = _steel_mass_kg(spec, raf_sec, col_sec)
    return DesignResult(
        frame_spec=spec,
        sections=section_choices,
        checks=all_checks,
        rules_version=code.rules_version(),
        warnings=tuple(warnings),
        total_steel_mass_kg=mass_kg,
        indicative_cost_zar=mass_kg * cost_rate_zar_per_kg,
        connections=connections,
        baseplate=baseplate,
        footing=footing,
        wind=wind_loads(spec),
        diagram=compute_frame_diagram(spec, raf_sec, col_sec),
    )


# ---------------------------------------------------------------------------
# The "last mile" — connections, baseplate, footing (Task 1.18)
# ---------------------------------------------------------------------------

def _design_last_mile(
    spec: FrameSpec,
    raf_sec: SectionProperties,
    col_sec: SectionProperties,
    code: DesignCode = DEFAULT_CODE,
) -> tuple[
    tuple[ConnectionDesignResult, ...],
    BaseplateDesignResult,
    PadFootingDesignResult | None,
]:
    """Design the eaves + apex connections, the column baseplate and (if an allowable
    bearing pressure is supplied) the pad footing, for the FINAL chosen sections.

    Re-runs the ULS-1 analysis (for joint + base forces) and an SLS-1 analysis (for the
    service base axial used in the geotechnical bearing check). All forces come from the
    deterministic kernel (PyNite). Connections/baseplate are always designed; the footing
    is designed only when ``spec.foundation.allowable_bearing_kpa`` is provided (never
    assumed — PRD FR-2/FR-30).
    """
    combos = {c.name.split()[0]: c for c in code.load_combinations(spec)}
    uls1 = _combo_starting_with(combos, "ULS-1")
    sls1 = _combo_starting_with(combos, "SLS-1")
    imposed = imposed_roof_loads(spec)
    grade = spec.materials.steel_grade

    gamma_G = uls1.factors["dead"]
    gamma_Q = uls1.factors.get("imposed", 0.0)
    dead = dead_loads(spec, rafter=raf_sec, column=col_sec)

    uls_rafter_udl = gamma_G * dead.rafter_udl_kn_per_m + gamma_Q * imposed.roof_udl_kn_per_m
    uls_col_udl = gamma_G * (dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m)
    uls_forces = {
        f.location: f
        for f in PortalAnalysis(spec, col_sec, raf_sec).run(uls1.name, uls_rafter_udl, uls_col_udl).forces
    }

    sls_rafter_udl = GAMMA_G_SLS_UNFAVOURABLE * dead.rafter_udl_kn_per_m + GAMMA_Q_SLS * imposed.roof_udl_kn_per_m
    sls_col_udl = GAMMA_G_SLS_UNFAVOURABLE * (
        dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m
    )
    sls_forces = {
        f.location: f
        for f in PortalAnalysis(spec, col_sec, raf_sec).run(sls1.name, sls_rafter_udl, sls_col_udl).forces
    }

    # --- connections (eaves + apex) — axial passed negative (compression: no bolt tension) ---
    eaves = code.design_connection(
        location="eaves",
        moment_knm=abs(uls_forces["eaves_L"].moment_knm),
        shear_kn=abs(uls_forces["eaves_L"].shear_kn),
        axial_kn=-abs(uls_forces["eaves_L"].axial_kn),
        member_depth_mm=raf_sec.depth_mm,
        member_flange_width_mm=raf_sec.width_mm,
        member_flange_thickness_mm=raf_sec.flange_thickness_mm,
        steel_grade=grade,
    )
    apex = code.design_connection(
        location="apex",
        moment_knm=abs(uls_forces["apex"].moment_knm),
        shear_kn=abs(uls_forces["apex"].shear_kn),
        axial_kn=-abs(uls_forces["apex"].axial_kn),
        member_depth_mm=raf_sec.depth_mm,
        member_flange_width_mm=raf_sec.width_mm,
        member_flange_thickness_mm=raf_sec.flange_thickness_mm,
        steel_grade=grade,
    )

    # --- baseplate (compression axial positive) ---
    baseplate = code.design_baseplate(
        base_fixity=spec.base_fixity.value,
        axial_kn=abs(uls_forces["col_base_L"].axial_kn),
        shear_kn=abs(uls_forces["col_base_L"].shear_kn),
        moment_knm=abs(uls_forces["col_base_L"].moment_knm),
        column_depth_mm=col_sec.depth_mm,
        column_flange_width_mm=col_sec.width_mm,
        steel_grade=grade,
        fc_mpa=spec.foundation.concrete_fcu_mpa,
    )

    # --- pad footing (only if allowable bearing pressure supplied) ---
    footing: PadFootingDesignResult | None = None
    if spec.foundation.allowable_bearing_kpa is not None:
        footing = code.design_footing(
            service_axial_kn=abs(sls_forces["col_base_L"].axial_kn),
            factored_axial_kn=abs(uls_forces["col_base_L"].axial_kn),
            allowable_bearing_kpa=spec.foundation.allowable_bearing_kpa,
            column_size_mm=max(col_sec.depth_mm, col_sec.width_mm),
            fcu_mpa=spec.foundation.concrete_fcu_mpa,
        )

    return (eaves, apex), baseplate, footing


def _last_mile_checks(
    connections: tuple[ConnectionDesignResult, ...],
    baseplate: BaseplateDesignResult,
    footing: PadFootingDesignResult | None,
) -> list[CheckResult]:
    """Flatten the connection/baseplate/footing checks for the aggregated `checks` list."""
    checks: list[CheckResult] = []
    for conn in connections:
        checks.extend(conn.checks)
    checks.extend(baseplate.checks)
    if footing is not None:
        checks.extend(footing.checks)
    return checks


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _combo_starting_with(
    combos: dict[str, LoadCombination], prefix: str
) -> LoadCombination:
    """Return the first LoadCombination whose name starts with *prefix*."""
    for name, combo in combos.items():
        if name.startswith(prefix):
            return combo
    raise KeyError(f"No load combination starting with {prefix!r} in: {list(combos)}")


def _steel_mass_kg(
    spec: FrameSpec,
    raf_sec: SectionProperties,
    col_sec: SectionProperties,
) -> float:
    """Per-frame steel mass (kg): 2 rafter halves + 2 columns.

    Formula: 2 × rafter_half_len_m × raf.mass_kg_m + 2 × eaves_h_m × col.mass_kg_m
    """
    geom = spec.geometry
    rafter_half_len_m = math.hypot(
        geom.span_m / 2.0,
        geom.apex_height_m - geom.eaves_height_m,
    )
    return (
        2.0 * rafter_half_len_m * raf_sec.mass_per_metre_kg_m
        + 2.0 * geom.eaves_height_m * col_sec.mass_per_metre_kg_m
    )


def _run_checks_safe(
    section: SectionProperties,
    fy_mpa: float,
    cu_kn: float,
    vu_kn: float,
    mu_knm: float,
    KL_mm: float,
    LTB_mm: float,
    member: str,
    code: DesignCode = DEFAULT_CODE,
) -> list[CheckResult]:
    """Run member checks, converting SectionIneligibleError to a failed CheckResult."""
    try:
        return run_member_checks(section, fy_mpa, cu_kn, vu_kn, mu_knm,
                                  KL_mm, LTB_mm, member=member, code=code)
    except SectionIneligibleError as exc:
        return [CheckResult(
            name=f"{member}: section ineligible",
            clause="SANS 10162-1:2011 cl. 11.2 / cl. 10.4.2.1",
            utilisation=float("inf"),
            passed=False,
            detail=str(exc),
        )]
