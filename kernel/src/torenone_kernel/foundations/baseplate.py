"""Column baseplate design — pinned & fixed (Task 1.16).

A steel baseplate transfers the column base reactions (axial N, shear V, moment M)
into the concrete. Limit states checked, each a CheckResult with clause + utilisation:
  * concrete bearing under the plate (elastic N+M pressure),
  * plate plastic bending of the cantilever overhang,
  * anchor-bolt tension (moment couple + uplift),
  * anchor-bolt shear.

Pinned bases (M ≈ 0) reduce to bearing + plate + nominal anchors; fixed bases add the
moment contribution. ``design_baseplate`` auto-sizes plate dimensions, thickness and
anchors from a small ladder.

⚠️ PROVISIONAL — the SANS 10162-1 resistance factors are now transcribed from the official
PDF (φc = 0.60 cl. 13.1(j); anchors are holding-down bolts → φar = 0.67 cl. 13.1(i); plate
flexure φ = 0.90 cl. 13.1(a)). The bearing *model* (elastic pressure block, 0.85·f'c, no
confinement A2/A1 benefit) and the conservative anchor-tension treatment (axial relief
ignored) remain engineering modelling choices to be confirmed against SANS 10100-1 cl. 4.10
bearing; final registered-engineer sign-off is still required.
"""

from __future__ import annotations

import dataclasses

from torenone_kernel.connections.bolts import (
    PHI_AR,
    BoltSpec,
    bolt_shear_resistance_kn,
    bolt_tension_resistance_kn,
    make_bolt,
)
from torenone_kernel.models.enums import SteelGrade
from torenone_kernel.models.results import BaseplateDesignResult, CheckResult

PHI_C: float = 0.60            # cl. 13.1(j) — concrete (resistance factor)
_BEARING_COEFF: float = 0.85   # 0.85·f'c bearing strength (conservative; no A2/A1 — PROVISIONAL)
_PHI_PLATE: float = 0.90       # cl. 13.1(a) — structural steel (plate flexure)
_DEFAULT_FC_MPA: float = 25.0  # concrete cylinder strength (PROVISIONAL default)

# AISC-style cantilever overhang factors (PROVISIONAL).
_DEPTH_FACTOR: float = 0.95
_FLANGE_FACTOR: float = 0.80

# Plate yield by grade for typical baseplate thickness (MPa) — PROVISIONAL.
_PLATE_FY: dict[SteelGrade, float] = {SteelGrade.S355JR: 345.0, SteelGrade.S275JR: 265.0}

# Auto-designer ladders (ascending).
_OVERHANGS_MM: tuple[float, ...] = (50.0, 75.0, 100.0, 150.0)
_THICKNESSES_MM: tuple[float, ...] = (12.0, 16.0, 20.0, 25.0, 32.0, 40.0)
_ANCHORS: tuple[BoltSpec, ...] = (make_bolt("M20", "8.8"), make_bolt("M24", "8.8"), make_bolt("M30", "8.8"))


@dataclasses.dataclass(frozen=True)
class BasePlate:
    """A baseplate configuration."""

    length_mm: float            # N — plate length (in the moment / column-depth plane)
    width_mm: float             # B — plate width
    thickness_mm: float
    plate_fy_mpa: float
    fc_mpa: float
    anchor: BoltSpec
    n_anchors_total: int        # all anchors (resist shear)
    n_anchors_tension: int      # anchors on the tension side
    anchor_lever_mm: float      # lever arm of the moment couple (anchor → compression)
    column_depth_mm: float
    column_flange_width_mm: float


def check_baseplate(
    plate: BasePlate,
    *,
    base_fixity: str,
    axial_kn: float,
    shear_kn: float,
    moment_knm: float = 0.0,
) -> list[CheckResult]:
    """Return the baseplate limit-state checks.

    *axial_kn* is signed: +ve = compression, −ve = net uplift (tension). *moment_knm*
    and *shear_kn* are magnitudes.
    """
    area_mm2 = plate.length_mm * plate.width_mm
    section_mod = plate.width_mm * plate.length_mm**2 / 6.0   # mm³
    compression_kn = max(axial_kn, 0.0)

    # --- 1. concrete bearing (elastic N + M peak pressure) ---
    p_axial = compression_kn * 1_000.0 / area_mm2            # MPa
    p_moment = moment_knm * 1_000_000.0 / section_mod        # MPa
    p_max = p_axial + p_moment
    bearing_cap = PHI_C * _BEARING_COEFF * plate.fc_mpa      # MPa
    u_bearing = p_max / bearing_cap

    # --- 2. plate cantilever bending under peak pressure ---
    overhang_len = (plate.length_mm - _DEPTH_FACTOR * plate.column_depth_mm) / 2.0
    overhang_wid = (plate.width_mm - _FLANGE_FACTOR * plate.column_flange_width_mm) / 2.0
    m_cant = max(overhang_len, overhang_wid, 1.0)
    moment_demand = p_max * m_cant**2 / 2.0                  # N·mm per mm width
    moment_cap = _PHI_PLATE * plate.plate_fy_mpa * plate.thickness_mm**2 / 4.0
    u_plate = moment_demand / moment_cap

    # --- 3. anchor tension (moment couple + uplift; axial relief ignored — conservative) ---
    t_moment = moment_knm * 1_000.0 / plate.anchor_lever_mm  # kN
    t_uplift = max(-axial_kn, 0.0)                           # kN
    t_total = t_moment + t_uplift
    # Anchors are holding-down bolts → φar = 0.67 (cl. 13.1(i)), not φb.
    tr_group = plate.n_anchors_tension * bolt_tension_resistance_kn(plate.anchor, phi=PHI_AR)
    u_anchor_t = t_total / tr_group if tr_group > 0 else 0.0

    # --- 4. anchor shear (shared by all anchors) ---
    v_per_anchor = shear_kn / plate.n_anchors_total
    vr_anchor = bolt_shear_resistance_kn(plate.anchor, phi=PHI_AR)
    u_anchor_v = v_per_anchor / vr_anchor

    prov = "PROVISIONAL"

    def _chk(name: str, clause: str, util: float, detail: str) -> CheckResult:
        return CheckResult(
            name=name, clause=clause, utilisation=round(util, 4),
            passed=util <= 1.0, detail=detail,
        )

    return [
        _chk("baseplate: concrete bearing",
             f"SANS 10162-1:2011 cl. 13.1(j) φc + SANS 10100-1 cl. 4.10 (bearing) — {prov}",
             u_bearing,
             f"p={p_max:.2f} MPa / {bearing_cap:.2f} MPa "
             f"({plate.length_mm:.0f}x{plate.width_mm:.0f} plate, f'c={plate.fc_mpa:.0f})"),
        _chk("baseplate: plate bending",
             f"SANS 10162-1:2011 cl. 13.5 (plate flexure) — {prov}", u_plate,
             f"{plate.thickness_mm:.0f} mm plate, cantilever m={m_cant:.0f} mm"),
        _chk("baseplate: anchor tension",
             f"SANS 10162-1:2011 cl. 13.1(i)/13.12 (anchors, tension) — {prov}", u_anchor_t,
             f"Tu={t_total:.1f} kN / Tr={tr_group:.1f} kN "
             f"({plate.n_anchors_tension}× {plate.anchor.designation}, {base_fixity})"),
        _chk("baseplate: anchor shear",
             f"SANS 10162-1:2011 cl. 13.1(i)/13.12 (anchors, shear) — {prov}", u_anchor_v,
             f"Vu={v_per_anchor:.1f} kN / Vr={vr_anchor:.1f} kN per anchor"),
    ]


def design_baseplate(
    *,
    base_fixity: str,
    axial_kn: float,
    shear_kn: float,
    moment_knm: float,
    column_depth_mm: float,
    column_flange_width_mm: float,
    steel_grade: SteelGrade,
    fc_mpa: float = _DEFAULT_FC_MPA,
) -> BaseplateDesignResult:
    """Auto-design the column baseplate for the base reactions.

    Iterates plate overhang → thickness → anchor size and returns the first
    configuration that passes every check; otherwise the strongest tried (with failing
    utilisations). All values are kernel-computed.
    """
    plate_fy = _PLATE_FY.get(steel_grade, 345.0)
    n_total, n_tension = 4, 2   # 2 anchors per side (PROVISIONAL standard layout)

    strongest: BaseplateDesignResult | None = None

    for anchor in _ANCHORS:
        for overhang in _OVERHANGS_MM:
            length = column_depth_mm + 2.0 * overhang
            width = column_flange_width_mm + 2.0 * overhang
            anchor_lever = length - 2.0 * (overhang / 2.0)   # anchors near plate edges
            for thickness in _THICKNESSES_MM:
                plate = BasePlate(
                    length_mm=length, width_mm=width, thickness_mm=thickness,
                    plate_fy_mpa=plate_fy, fc_mpa=fc_mpa, anchor=anchor,
                    n_anchors_total=n_total, n_anchors_tension=n_tension,
                    anchor_lever_mm=anchor_lever,
                    column_depth_mm=column_depth_mm,
                    column_flange_width_mm=column_flange_width_mm,
                )
                checks = check_baseplate(
                    plate, base_fixity=base_fixity, axial_kn=axial_kn,
                    shear_kn=shear_kn, moment_knm=moment_knm,
                )
                result = BaseplateDesignResult(
                    base_fixity=base_fixity,
                    description=(
                        f"{length:.0f}x{width:.0f}x{thickness:.0f} mm plate "
                        f"({steel_grade.value}), 4× {anchor.designation} grade "
                        f"{anchor.grade} anchors, f'c={fc_mpa:.0f} MPa"
                    ),
                    design_axial_kn=axial_kn,
                    design_shear_kn=shear_kn,
                    design_moment_knm=moment_knm,
                    checks=checks,
                )
                if result.passed:
                    return result
                strongest = result

    assert strongest is not None
    return strongest
