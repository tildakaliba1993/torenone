"""Simple concrete pad footing — SANS 10100-1 (SABS 0100-1 Ed. 2.2) (Task 1.17).

Sizes a square reinforced-concrete pad under a portal column base from the column base
reactions, against an **engineer-supplied allowable bearing pressure** (never assumed).
Limit states, each a CheckResult with clause + utilisation:
  * soil bearing — service load + footing self-weight vs allowable (geotechnical input);
  * maximum shear at the column face         (cl. 4.3.4.1 / 4.10.4.4);
  * punching shear on the 1.5·d perimeter    (cl. 4.4.5 / 4.10.4.4);
  * one-way (beam) shear at d from the face  (cl. 4.3.4);
  * flexure → reinforcement (bending critical section at the column face, cl. 4.3.3.4 /
    4.10.2.2), with the cl. 4.11.4 minimum-reinforcement floor.

Verified against SANS 10100-1 (the PDF is in `standards/`):
  * flexure stress block 0.67·fcu/γc (γc=1.5), steel fy/γs (γs=1.15), lever arm ≤ 0.95d,
    K' = 0.156 — cl. 4.3.3.1 + Fig. 4 + cl. 4.3.3.4;
  * design concrete shear stress vc = (0.75/γm)(fcu/25)^⅓(100As/bd)^⅓(400/d)^¼,
    γm = 1.4 — cl. 4.3.4 eq. (2);
  * maximum shear stress v_max = min(0.75·√fcu, 4.75) MPa — cl. 4.3.4.1;
  * uniform bearing pressure for an axially-loaded base — cl. 4.10.2.1.

The allowable bearing pressure is a site/geotechnical value the engineer supplies (not a
SANS 10100-1 quantity). Material defaults (fcu=25 MPa, fy=450 MPa, cover=50 mm) are
typical SA values; durability/fire cover and full detailing remain the engineer's check.
"""

from __future__ import annotations

import dataclasses
import math

from torenone_kernel.models.results import CheckResult, PadFootingDesignResult

GAMMA_CONCRETE_KN_M3: float = 24.0     # reinforced-concrete unit weight
GAMMA_M_SHEAR: float = 1.4             # cl. 4.3.4 — concrete shear material factor
K_PRIME: float = 0.156                 # cl. 4.3.3.4 — singly-reinforced limit (no redistribution)
_VC_COEFF: float = 0.75                # cl. 4.3.4 eq. (2)
_MIN_STEEL_RATIO: float = 0.0013       # cl. 4.11.4 — min 0.13 % (high-yield) of gross section
_FCU_CAP_MPA: float = 40.0             # cl. 4.3.4 — fcu in vc capped at 40

_DEFAULT_FCU_MPA: float = 25.0         # characteristic cube strength (typical SA)
_DEFAULT_FY_REBAR_MPA: float = 450.0   # high-yield reinforcement (typical SA)
_DEFAULT_COVER_MM: float = 50.0        # nominal cover (typical; durability check separate)

# Auto-designer ladders (ascending).
_THICKNESSES_MM: tuple[float, ...] = (300.0, 400.0, 500.0, 600.0, 750.0, 900.0)
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


def design_concrete_shear_stress_vc(fcu_mpa: float, as_mm2_per_m: float, d_mm: float) -> float:
    """SANS 10100-1 cl. 4.3.4 eq. (2): vc = (0.75/γm)(fcu/25)^⅓(100As/bd)^⅓(400/d)^¼ (MPa).

    Per metre width (b = 1000 mm). (100·As/bd) is capped at 3 and fcu at 40 (cl. 4.3.4).
    """
    rho_term = min(100.0 * as_mm2_per_m / (1_000.0 * d_mm), 3.0)
    fcu_term = min(fcu_mpa, _FCU_CAP_MPA) / 25.0
    return float(
        (_VC_COEFF / GAMMA_M_SHEAR)
        * fcu_term ** (1.0 / 3.0)
        * rho_term ** (1.0 / 3.0)
        * (400.0 / d_mm) ** 0.25
    )


def max_shear_stress_vmax(fcu_mpa: float) -> float:
    """SANS 10100-1 cl. 4.3.4.1: v_max = lesser of 0.75·√fcu or 4.75 MPa."""
    return min(0.75 * math.sqrt(fcu_mpa), 4.75)


def check_pad_footing(
    footing: PadFooting,
    *,
    service_axial_kn: float,
    factored_axial_kn: float,
    allowable_bearing_kpa: float,
) -> list[CheckResult]:
    """Return the pad-footing limit-state checks (axial compression, magnitudes)."""
    b_m = footing.plan_size_mm / 1_000.0
    d_m = footing.thickness_mm / 1_000.0
    area_m2 = b_m * b_m
    d_mm = _effective_depth_mm(footing)
    c_mm = footing.column_size_mm
    fcu = footing.fcu_mpa

    as_prov = _provided_steel_area_mm2_per_m(footing)
    vc = design_concrete_shear_stress_vc(fcu, as_prov, d_mm)
    v_max = max_shear_stress_vmax(fcu)

    # --- 1. soil bearing (service, vs engineer-supplied allowable) ---
    self_weight_kn = area_m2 * d_m * GAMMA_CONCRETE_KN_M3
    gross_pressure_kpa = (service_axial_kn + self_weight_kn) / area_m2
    u_bearing = gross_pressure_kpa / allowable_bearing_kpa

    # net upward (factored) soil pressure for structural design (self-weight cancels)
    net_pressure_kpa = factored_axial_kn / area_m2

    # --- 2. maximum shear stress at the column face (cl. 4.3.4.1 / 4.10.4.4) ---
    v_face = factored_axial_kn * 1_000.0 / (4.0 * c_mm * d_mm)   # MPa
    u_face = v_face / v_max

    # --- 3. punching shear on the 1.5·d perimeter (cl. 4.4.5 / 4.10.4.4) ---
    side_in_mm = c_mm + 3.0 * d_mm                               # column + 2×1.5d
    perimeter_mm = 4.0 * side_in_mm
    inside_fraction = min((side_in_mm / 1_000.0) ** 2 / area_m2, 1.0)
    v_punch_force_kn = factored_axial_kn * (1.0 - inside_fraction)
    v_punch = v_punch_force_kn * 1_000.0 / (perimeter_mm * d_mm)  # MPa
    u_punch = v_punch / vc

    # --- 4. one-way (beam) shear at d from the column face (cl. 4.3.4) ---
    projection_m = (b_m - c_mm / 1_000.0) / 2.0
    shear_span_m = max(projection_m - d_mm / 1_000.0, 0.0)
    v_oneway_kn = net_pressure_kpa * b_m * shear_span_m
    v_oneway = v_oneway_kn * 1_000.0 / (footing.plan_size_mm * d_mm)  # MPa
    u_oneway = v_oneway / vc

    # --- 5. flexure (cantilever at the column face) + reinforcement (cl. 4.3.3.4) ---
    moment_knm_per_m = net_pressure_kpa * projection_m**2 / 2.0
    moment_nmm = moment_knm_per_m * 1_000_000.0
    k_factor = moment_nmm / (1_000.0 * d_mm**2 * fcu)
    z_mm = min(0.95 * d_mm, d_mm * (0.5 + math.sqrt(max(0.25 - k_factor / 0.9, 0.0))))
    as_from_moment = moment_nmm / (0.87 * footing.fy_rebar_mpa * z_mm)        # mm²/m
    as_min = _MIN_STEEL_RATIO * 1_000.0 * footing.thickness_mm                # cl. 4.11.4
    as_req = max(as_from_moment, as_min)
    # over-reinforced (K > K') captured so the check fails before z goes imaginary
    u_flexure = max(as_req / as_prov, k_factor / K_PRIME)

    def _chk(name: str, clause: str, util: float, detail: str) -> CheckResult:
        return CheckResult(
            name=name, clause=clause, utilisation=round(util, 4),
            passed=util <= 1.0, detail=detail,
        )

    return [
        _chk("footing: soil bearing",
             "Geotechnical — engineer-supplied allowable bearing (serviceability)", u_bearing,
             f"p={gross_pressure_kpa:.0f} kPa / {allowable_bearing_kpa:.0f} kPa allowable "
             f"({footing.plan_size_mm:.0f} mm square)"),
        _chk("footing: max shear at column face",
             "SANS 10100-1 cl. 4.3.4.1 / 4.10.4.4 (v_max)", u_face,
             f"v={v_face:.2f} MPa / v_max={v_max:.2f} MPa"),
        _chk("footing: punching shear (1.5d)",
             "SANS 10100-1 cl. 4.4.5 / 4.10.4.4", u_punch,
             f"v={v_punch:.2f} MPa / vc={vc:.2f} MPa on 1.5d perimeter"),
        _chk("footing: one-way shear",
             "SANS 10100-1 cl. 4.3.4 (eq. 2 vc)", u_oneway,
             f"v={v_oneway:.2f} MPa / vc={vc:.2f} MPa at d from face"),
        _chk("footing: flexure / reinforcement",
             "SANS 10100-1 cl. 4.3.3.4 / 4.10.2.2", u_flexure,
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
    for _ in range(60):   # bounded growth to include self-weight
        area = (plan / 1_000.0) ** 2
        self_weight = area * 0.45 * GAMMA_CONCRETE_KN_M3   # assume ~450 mm for sizing
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
