"""Simple concrete pad footing — SANS 10100-1 (Task 1.17).

Sizes a square reinforced-concrete pad under a portal column base, from the column
base reactions, against an **engineer-supplied allowable bearing pressure** (never
assumed). Limit states checked, each a CheckResult with clause + utilisation:
  * soil bearing (service load + footing self-weight vs allowable),
  * punching shear at the column/baseplate perimeter,
  * one-way (beam) shear at d from the column face,
  * flexure — cantilever moment from the net upward pressure → reinforcement.

⚠️⚠️ PROVISIONAL — this crosses into **concrete design (SANS 10100-1)**, a different
standard than the steel kernel, whose clauses were NOT available in `standards/`.
ALL coefficients (γc=1.5, design stresses, shear limits, the BS 8110-lineage lever-arm
formula) follow established SANS 10100-1 / BS 8110 practice and are flagged PROVISIONAL,
pending a registered (preferably concrete-experienced) engineer's verification. The
allowable bearing pressure is a site/geotechnical input the engineer must provide.
"""

from __future__ import annotations

import dataclasses
import math

from torenone_kernel.models.results import CheckResult, PadFootingDesignResult

GAMMA_CONCRETE_KN_M3: float = 24.0   # reinforced-concrete unit weight
_DEFAULT_FCU_MPA: float = 25.0       # characteristic cube strength (PROVISIONAL)
_DEFAULT_FY_REBAR_MPA: float = 450.0  # high-yield reinforcement (PROVISIONAL)
_DEFAULT_COVER_MM: float = 50.0      # nominal cover to reinforcement (PROVISIONAL)
_K_BALANCED: float = 0.156           # singly-reinforced limit (BS 8110 / SANS 10100-1)
_VC_ONEWAY_MPA: float = 0.75         # nominal design concrete shear stress (PROVISIONAL)

# Auto-designer ladders (ascending).
_THICKNESSES_MM: tuple[float, ...] = (300.0, 400.0, 500.0, 600.0, 750.0, 900.0)
# (bar diameter mm, spacing mm) in ascending steel-area order
_REBAR_LADDER: tuple[tuple[float, float], ...] = (
    (12.0, 200.0), (16.0, 200.0), (16.0, 150.0), (20.0, 150.0), (20.0, 100.0), (25.0, 100.0),
)


@dataclasses.dataclass(frozen=True)
class PadFooting:
    """A square pad-footing configuration."""

    plan_size_mm: float        # B (square)
    thickness_mm: float        # D
    cover_mm: float
    bar_diameter_mm: float
    bar_spacing_mm: float
    fcu_mpa: float
    fy_rebar_mpa: float
    column_size_mm: float      # loaded patch (≈ baseplate side) for punching/cantilever


def _effective_depth_mm(footing: PadFooting) -> float:
    return footing.thickness_mm - footing.cover_mm - footing.bar_diameter_mm / 2.0


def _provided_steel_area_mm2_per_m(footing: PadFooting) -> float:
    bars_per_m = 1_000.0 / footing.bar_spacing_mm
    bar_area = math.pi / 4.0 * footing.bar_diameter_mm**2
    return bars_per_m * bar_area


def check_pad_footing(
    footing: PadFooting,
    *,
    service_axial_kn: float,
    factored_axial_kn: float,
    allowable_bearing_kpa: float,
) -> list[CheckResult]:
    """Return the pad-footing limit-state checks (all magnitudes, axial compression)."""
    b_m = footing.plan_size_mm / 1_000.0
    d_m = footing.thickness_mm / 1_000.0
    area_m2 = b_m * b_m
    d_mm = _effective_depth_mm(footing)
    fcu = footing.fcu_mpa

    # --- 1. soil bearing (service) ---
    self_weight_kn = area_m2 * d_m * GAMMA_CONCRETE_KN_M3
    gross_pressure_kpa = (service_axial_kn + self_weight_kn) / area_m2
    u_bearing = gross_pressure_kpa / allowable_bearing_kpa

    # net upward (factored) soil pressure used for structural design (self-weight cancels)
    net_pressure_kpa = factored_axial_kn / area_m2

    # --- 2. punching shear at the column/baseplate face perimeter ---
    perimeter_mm = 4.0 * footing.column_size_mm
    v_punch_applied = factored_axial_kn * 1_000.0 / (perimeter_mm * d_mm)   # MPa (conservative)
    v_punch_max = min(0.75 * math.sqrt(fcu), 4.75)                         # MPa (PROVISIONAL)
    u_punch = v_punch_applied / v_punch_max

    # --- 3. one-way (beam) shear at d from the column face ---
    projection_m = (b_m - footing.column_size_mm / 1_000.0) / 2.0
    shear_span_m = max(projection_m - d_mm / 1_000.0, 0.0)
    v_oneway_kn = net_pressure_kpa * b_m * shear_span_m
    v_oneway_applied = v_oneway_kn * 1_000.0 / (footing.plan_size_mm * d_mm)  # MPa
    u_oneway = v_oneway_applied / _VC_ONEWAY_MPA

    # --- 4. flexure (cantilever at column face) + reinforcement ---
    moment_knm_per_m = net_pressure_kpa * projection_m**2 / 2.0
    moment_nmm = moment_knm_per_m * 1_000_000.0
    k_factor = moment_nmm / (1_000.0 * d_mm**2 * fcu)
    z_mm = min(0.95 * d_mm, d_mm * (0.5 + math.sqrt(max(0.25 - k_factor / 0.9, 0.0))))
    as_req = moment_nmm / (0.87 * footing.fy_rebar_mpa * z_mm)            # mm²/m
    as_prov = _provided_steel_area_mm2_per_m(footing)
    # over-reinforced (K > 0.156) is captured so the check fails before z goes imaginary
    u_flexure = max(as_req / as_prov, k_factor / _K_BALANCED)

    prov = "PROVISIONAL"

    def _chk(name: str, clause: str, util: float, detail: str) -> CheckResult:
        return CheckResult(
            name=name, clause=clause, utilisation=round(util, 4),
            passed=util <= 1.0, detail=detail,
        )

    return [
        _chk("footing: soil bearing",
             f"SANS 10100-1 (geotechnical/bearing) — {prov}", u_bearing,
             f"p={gross_pressure_kpa:.0f} kPa / {allowable_bearing_kpa:.0f} kPa allowable "
             f"({footing.plan_size_mm:.0f} mm square)"),
        _chk("footing: punching shear",
             f"SANS 10100-1 cl. 4.4.5 (punching) — {prov}", u_punch,
             f"v={v_punch_applied:.2f} MPa / {v_punch_max:.2f} MPa"),
        _chk("footing: one-way shear",
             f"SANS 10100-1 cl. 4.3.4 (beam shear) — {prov}", u_oneway,
             f"v={v_oneway_applied:.2f} MPa / {_VC_ONEWAY_MPA:.2f} MPa"),
        _chk("footing: flexure / reinforcement",
             f"SANS 10100-1 cl. 4.3.3 (flexure) — {prov}", u_flexure,
             f"As,req={as_req:.0f} / As,prov={as_prov:.0f} mm²/m "
             f"(Y{footing.bar_diameter_mm:.0f}@{footing.bar_spacing_mm:.0f}), K={k_factor:.3f}"),
    ]


def design_pad_footing(
    *,
    service_axial_kn: float,
    factored_axial_kn: float,
    allowable_bearing_kpa: float,
    column_size_mm: float,
    fcu_mpa: float = _DEFAULT_FCU_MPA,
    fy_rebar_mpa: float = _DEFAULT_FY_REBAR_MPA,
    cover_mm: float = _DEFAULT_COVER_MM,
) -> PadFootingDesignResult:
    """Auto-design a square pad footing for the column base reactions.

    Plan size B is set from soil bearing; thickness D and reinforcement are then chosen
    from ascending ladders. Returns the first all-passing configuration, else the
    strongest tried (with failing utilisations). All values are kernel-computed.
    """
    # Plan size from bearing: grow a 50 mm-module square until gross pressure passes.
    required_area = service_axial_kn / allowable_bearing_kpa
    plan = max(math.ceil(math.sqrt(required_area) * 1_000.0 / 50.0) * 50.0, 600.0)
    for _ in range(40):   # bounded growth to include self-weight
        area = (plan / 1_000.0) ** 2
        self_weight = area * (0.45) * GAMMA_CONCRETE_KN_M3   # assume ~450 mm for sizing
        if (service_axial_kn + self_weight) / area <= allowable_bearing_kpa:
            break
        plan += 50.0

    strongest: PadFootingDesignResult | None = None
    for thickness in _THICKNESSES_MM:
        for bar_dia, spacing in _REBAR_LADDER:
            footing = PadFooting(
                plan_size_mm=plan, thickness_mm=thickness, cover_mm=cover_mm,
                bar_diameter_mm=bar_dia, bar_spacing_mm=spacing,
                fcu_mpa=fcu_mpa, fy_rebar_mpa=fy_rebar_mpa, column_size_mm=column_size_mm,
            )
            checks = check_pad_footing(
                footing, service_axial_kn=service_axial_kn,
                factored_axial_kn=factored_axial_kn, allowable_bearing_kpa=allowable_bearing_kpa,
            )
            result = PadFootingDesignResult(
                description=(
                    f"{plan:.0f} mm square × {thickness:.0f} mm pad, "
                    f"Y{bar_dia:.0f}@{spacing:.0f} both ways, "
                    f"fcu={fcu_mpa:.0f} MPa, fy={fy_rebar_mpa:.0f} MPa"
                ),
                plan_size_mm=plan,
                thickness_mm=thickness,
                allowable_bearing_kpa=allowable_bearing_kpa,
                design_service_axial_kn=service_axial_kn,
                design_factored_axial_kn=factored_axial_kn,
                checks=checks,
            )
            if result.passed:
                return result
            strongest = result

    assert strongest is not None
    return strongest
