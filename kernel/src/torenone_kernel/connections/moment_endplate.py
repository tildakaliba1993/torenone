"""Bolted end-plate moment connection — eaves & apex of the portal frame (Task 1.15).

Method (flange-force-couple — a recognised *simplified* moment-connection method):
  * The design moment is resisted by a tension/compression couple at the member flanges:
        T_flange = Mu / z         (z = lever arm ≈ member depth − flange thickness)
  * The tension-flange force is shared equally by the tension bolts; any net tensile
    axial force is shared by all bolts. Shear is shared equally by all bolts.
  * Limit states checked, each a CheckResult with a clause ref + utilisation:
        bolt tension · bolt shear · bolt bearing · combined tension+shear ·
        end-plate plastic bending (T-stub, simplified) · flange fillet weld.

⚠️ PROVISIONAL — see the package docstring. Coefficients/φ follow SANS 10162-1 / CSA S16
practice but are not transcribed from the standard PDF; prying and yield-line modes 2/3
are not modelled. A registered engineer must verify before use.
"""

from __future__ import annotations

import dataclasses

from torenone_kernel.connections.bolts import (
    STANDARD_BOLTS,
    BoltSpec,
    bolt_bearing_resistance_kn,
    bolt_shear_resistance_kn,
    bolt_tension_resistance_kn,
)
from torenone_kernel.models.enums import SteelGrade
from torenone_kernel.models.results import CheckResult, ConnectionDesignResult

# Weld constants (SANS 10162-1 cl. 13.1 / 13.13.2.2 — PROVISIONAL).
PHI_W: float = 0.67          # resistance factor, welds
_WELD_COEFF: float = 0.67    # cl. 13.13.2.2 fillet-weld coefficient
_THROAT_FACTOR: float = 0.707  # fillet throat = 0.707 × leg
_DEFAULT_ELECTRODE_XU_MPA: float = 480.0   # E48xx electrode ultimate (PROVISIONAL)
_PHI_PLATE: float = 0.90     # plate flexure (cl. 13.1)

# Plate ultimate strength by grade (MPa) — PROVISIONAL.
_PLATE_FU: dict[SteelGrade, float] = {SteelGrade.S355JR: 470.0, SteelGrade.S275JR: 410.0}
# Plate yield by grade for typical end-plate thickness (MPa) — PROVISIONAL.
_PLATE_FY: dict[SteelGrade, float] = {SteelGrade.S355JR: 345.0, SteelGrade.S275JR: 265.0}

# Auto-designer ladders (ascending).
_PLATE_THICKNESSES_MM: tuple[float, ...] = (12.0, 16.0, 20.0, 25.0, 32.0)
_WELD_LEGS_MM: tuple[float, ...] = (6.0, 8.0, 10.0, 12.0)
_DEFAULT_BOLT_GAUGE_MM: float = 45.0   # bolt line to flange/weld (typical) — PROVISIONAL


@dataclasses.dataclass(frozen=True)
class EndPlateConnection:
    """A bolted end-plate moment connection configuration."""

    bolt: BoltSpec
    n_tension_bolts: int       # bolts resisting the tension-flange force
    n_total_bolts: int         # all bolts (resist shear)
    lever_arm_mm: float        # z between flange centroids
    plate_thickness_mm: float
    plate_fy_mpa: float
    plate_fu_mpa: float
    plate_trib_width_mm: float  # effective plate width per bolt (T-stub)
    bolt_to_weld_mm: float      # m — bolt line to flange/weld
    weld_leg_mm: float
    weld_length_mm: float       # total flange fillet-weld length
    electrode_xu_mpa: float = _DEFAULT_ELECTRODE_XU_MPA


def _weld_resistance_per_mm_kn(leg_mm: float, xu_mpa: float) -> float:
    """Fillet-weld factored resistance per mm: 0.67·φw·(0.707·leg)·Xu (cl. 13.13.2.2)."""
    vr_n_per_mm = _WELD_COEFF * PHI_W * (_THROAT_FACTOR * leg_mm) * xu_mpa
    return float(vr_n_per_mm / 1_000.0)


def check_moment_connection(
    conn: EndPlateConnection,
    moment_knm: float,
    shear_kn: float,
    axial_kn: float = 0.0,
) -> list[CheckResult]:
    """Return the connection limit-state checks for the given design forces.

    *moment_knm* and *shear_kn* are magnitudes; *axial_kn* is signed (tension +ve).
    """
    # --- demands ---
    t_flange_kn = moment_knm * 1_000.0 / conn.lever_arm_mm   # kN·m·1e3 / mm → kN
    axial_tension_per_bolt = max(axial_kn, 0.0) / conn.n_total_bolts
    tension_per_bolt = t_flange_kn / conn.n_tension_bolts + axial_tension_per_bolt
    shear_per_bolt = shear_kn / conn.n_total_bolts

    # --- capacities ---
    tr = bolt_tension_resistance_kn(conn.bolt)
    vr = bolt_shear_resistance_kn(conn.bolt)
    br = bolt_bearing_resistance_kn(conn.bolt, conn.plate_thickness_mm, conn.plate_fu_mpa)

    u_tension = tension_per_bolt / tr
    u_shear = shear_per_bolt / vr
    u_bearing = shear_per_bolt / br
    # Combined shear + tension (cl. 13.12.1.4, bearing-type): Vu/Vr + Tu/Tr ≤ 1.4.
    # Normalised by 1.4 so utilisation is comparable to the other checks (1.0 = at limit).
    u_combined = (u_tension + u_shear) / 1.4

    # end-plate plastic bending (T-stub, simplified)
    m_demand = (tension_per_bolt * 1_000.0) * conn.bolt_to_weld_mm   # N·mm
    m_cap = _PHI_PLATE * conn.plate_trib_width_mm * conn.plate_fy_mpa * conn.plate_thickness_mm**2 / 4.0
    u_plate = m_demand / m_cap

    # flange fillet weld
    weld_demand_per_mm = t_flange_kn / conn.weld_length_mm
    weld_cap_per_mm = _weld_resistance_per_mm_kn(conn.weld_leg_mm, conn.electrode_xu_mpa)
    u_weld = weld_demand_per_mm / weld_cap_per_mm

    def _chk(name: str, clause: str, util: float, detail: str) -> CheckResult:
        return CheckResult(
            name=name, clause=clause, utilisation=round(util, 4),
            passed=util <= 1.0, detail=detail,
        )

    prov = "PROVISIONAL"
    return [
        _chk("connection: bolt tension",
             f"SANS 10162-1:2011 cl. 13.12.1.3 (tension) — {prov}", u_tension,
             f"Tu={tension_per_bolt:.1f} kN / Tr={tr:.1f} kN per bolt"),
        _chk("connection: bolt shear",
             f"SANS 10162-1:2011 cl. 13.12.1.2 (shear) — {prov}", u_shear,
             f"Vu={shear_per_bolt:.1f} kN / Vr={vr:.1f} kN per bolt"),
        _chk("connection: bolt bearing",
             f"SANS 10162-1:2011 cl. 13.10(c) (bearing) — {prov}", u_bearing,
             f"Vu={shear_per_bolt:.1f} kN / Br={br:.1f} kN on {conn.plate_thickness_mm:.0f} mm plate"),
        _chk("connection: bolt tension+shear interaction",
             f"SANS 10162-1:2011 cl. 13.12.1.4 (interaction) — {prov}", u_combined,
             f"Tu/Tr+Vu/Vr={(u_tension + u_shear):.2f} ≤ 1.4"),
        _chk("connection: end-plate bending",
             f"SANS 10162-1:2011 cl. 13.13 (end-plate, T-stub) — {prov}", u_plate,
             f"{conn.plate_thickness_mm:.0f} mm plate, m={conn.bolt_to_weld_mm:.0f} mm"),
        _chk("connection: flange weld",
             f"SANS 10162-1:2011 cl. 13.13.2.2 (fillet weld) — {prov}", u_weld,
             f"{conn.weld_leg_mm:.0f} mm fillet, demand={weld_demand_per_mm:.2f} kN/mm "
             f"/ {weld_cap_per_mm:.2f} kN/mm"),
    ]


def design_moment_connection(
    *,
    location: str,
    moment_knm: float,
    shear_kn: float,
    axial_kn: float,
    member_depth_mm: float,
    member_flange_width_mm: float,
    member_flange_thickness_mm: float,
    steel_grade: SteelGrade,
) -> ConnectionDesignResult:
    """Auto-design the eaves/apex end-plate connection for the given member + forces.

    Iterates a small ladder of standard bolts → end-plate thicknesses → weld legs and
    returns the first configuration that passes every check. If none pass, returns the
    strongest configuration tried (with its failing utilisations) so the engineer sees
    how far short it falls. No computation is hidden — all values are kernel-computed.
    """
    lever_arm = max(member_depth_mm - member_flange_thickness_mm, 1.0)
    plate_fy = _PLATE_FY.get(steel_grade, 345.0)
    plate_fu = _PLATE_FU.get(steel_grade, 470.0)
    trib_width = member_flange_width_mm / 2.0     # 2 bolts across the flange width
    weld_length = 2.0 * member_flange_width_mm    # fillet both sides of the tension flange
    n_tension_bolts = 4                           # 2 rows × 2 (PROVISIONAL standard layout)
    n_total_bolts = 6                             # 3 rows × 2

    strongest: ConnectionDesignResult | None = None

    for bolt in STANDARD_BOLTS:
        for plate_t in _PLATE_THICKNESSES_MM:
            for weld_leg in _WELD_LEGS_MM:
                conn = EndPlateConnection(
                    bolt=bolt,
                    n_tension_bolts=n_tension_bolts,
                    n_total_bolts=n_total_bolts,
                    lever_arm_mm=lever_arm,
                    plate_thickness_mm=plate_t,
                    plate_fy_mpa=plate_fy,
                    plate_fu_mpa=plate_fu,
                    plate_trib_width_mm=trib_width,
                    bolt_to_weld_mm=_DEFAULT_BOLT_GAUGE_MM,
                    weld_leg_mm=weld_leg,
                    weld_length_mm=weld_length,
                )
                checks = check_moment_connection(conn, moment_knm, shear_kn, axial_kn)
                result = ConnectionDesignResult(
                    location=location,
                    description=(
                        f"{bolt.designation} grade {bolt.grade} bolts "
                        f"({n_tension_bolts} tension / {n_total_bolts} total), "
                        f"{plate_t:.0f} mm end-plate, {weld_leg:.0f} mm fillet weld"
                    ),
                    design_moment_knm=moment_knm,
                    design_shear_kn=shear_kn,
                    design_axial_kn=axial_kn,
                    checks=checks,
                )
                if result.passed:
                    return result
                strongest = result   # last (strongest) tried so far

    assert strongest is not None   # ladders are non-empty
    return strongest
