"""Column base design — SANS 10100 / BS 5950 effective-area method (Mahachi textbook §7.9).

⚠️ PROVISIONAL — transcribed clause-for-clause from an **accredited published South African
source**: Mahachi, *Design of Structural Steelwork to SANS 10162* (CSIR, 2004; author
J Mahachi Pr.Eng PhD), §7.9.2 (slab bases) and §7.9.3 (base subject to axial load + moment),
worked Examples **E7.13** and **E7.14**. Every routine here reproduces that book's published
worked answers to the millimetre — proven in
``kernel/tests/validation/textbook/test_textbook_column_base.py``.

Why this module exists
----------------------
The existing baseplate engine (``foundations/baseplate.py``) is an **AISC-style** model
(elastic pressure block, 0.85·f'c cylinder bearing, US cantilever-overhang plate sizing).
Both South African authorities we validate against — the SAISC Red Book §4.2.2 **and** this
Mahachi textbook §7.9 — instead use the **SANS 10100 / BS 5950 effective-area method**
(0.4·fcu cube bearing, effective-area plate sizing, a rectangular concrete stress block for the
axial-plus-moment case, and holding-down bolts checked on the *tensile-stress area* via the
concrete code). The two idealisations diverge at every step and give different numbers, so the
column base was the one place our engine did **not** reproduce the SA authorities. This module
implements the SA authorities' method so we can.

This module is deliberately **NOT wired into the live design path** — it awaits registered-
engineer sign-off to replace the AISC-style baseplate. See ``docs/REDBOOK-VALIDATION.md``.

Method (clause tags refer to SANS 10100-1:1992 / SANS 10162-1):
  * Concrete bearing resistance  Br = 0.4·fcu        (SANS 10100-1 cl. 3.5.3)
  * Plate flexure (1 mm strip)   M = p·a²/2, f = φ·fy → tp = a·√(3p/(φ·fy))   (§7.9.2)
  * Axial+moment base            rectangular stress block Cu = b·d2·Br, Tu = Cu − Pu   (§7.9.3)
  * Holding-down bolt tension    Tr = n·φar·An·fu   (SANS 10100-1 cl. 25.2.2.1; An = stress area)
  * Gussets / welds              clause 13.5 / 13.4.1.1 / 13.13.2.2 fillet welds
"""

from __future__ import annotations

import dataclasses
import math

# Resistance factors.
PHI_PLATE: float = 0.90    # SANS 10162-1 cl. 13.1(a) — structural steel (plate / gusset flexure)
PHI_ANCHOR: float = 0.67   # SANS 10100-1 cl. 25.2.2.1 — holding-down (anchor) bolts in tension
PHI_WELD: float = 0.67     # SANS 10162-1 cl. 13.1 — weld metal
_WELD_FORMULA_COEFF: float = 0.67   # cl. 13.13.2.2 — Vr = 0.67·φw·Aw·Xu (longitudinal, θ=0)
_WELD_THROAT_FACTOR: float = 0.707  # throat = 0.707 × leg for an equal-leg fillet

_BEARING_COEFF_FCU: float = 0.40    # Br = 0.4·fcu (cube strength), SANS 10100-1 cl. 3.5.3

# Standard plate thicknesses (mm), ascending — for rounding up a computed thickness.
STANDARD_PLATE_THICKNESSES_MM: tuple[float, ...] = (8, 10, 12, 16, 20, 25, 30, 35, 40, 50)
# Standard fillet-weld leg sizes (mm), ascending.
STANDARD_WELD_LEGS_MM: tuple[float, ...] = (5, 6, 8, 10, 12, 14, 16, 18, 20)
# ISO metric coarse-thread tensile stress area Aₛ (mm²) — used for holding-down bolts (the SANS
# 10100 anchorage check uses the tensile-stress area, NOT the nominal shank area).
BOLT_STRESS_AREA_MM2: dict[str, float] = {
    "M16": 157.0, "M20": 245.0, "M24": 353.0, "M30": 561.0, "M36": 817.0,
}

# Electrode classification ultimate strength Xu (MPa). E80XX ≈ 80 ksi ≈ 550 MPa (the book's choice).
XU_E80XX_MPA: float = 550.0


def _round_up(value: float, ladder: tuple[float, ...]) -> float:
    """Return the first ladder entry ≥ *value* (or the largest entry if none qualifies)."""
    for entry in ladder:
        if entry >= value - 1e-9:
            return entry
    return ladder[-1]


def concrete_bearing_resistance_mpa(fcu_mpa: float) -> float:
    """Factored bearing resistance of the concrete, Br = 0.4·fcu (SANS 10100-1 cl. 3.5.3).

    fcu is the **cube** strength. 20 MPa → 8 MPa; 25 MPa → 10 MPa.
    """
    return _BEARING_COEFF_FCU * fcu_mpa


def plate_thickness_from_pressure_mm(
    projection_mm: float, pressure_mpa: float, *, fy_mpa: float = 300.0, phi: float = PHI_PLATE
) -> float:
    """Plate thickness for a 1 mm cantilever strip under uniform pressure (§7.9.2, eq. 7.56–7.58).

    A strip of overhang ``a`` under pressure ``p`` has M = p·a²/2; setting the bending stress
    f = M·6/t² equal to φ·fy and solving: ``t = a·√(3p/(φ·fy))``. For Grade 300W with p = Br this
    reduces to the book's t = 0.30a (20 MPa) / 0.33a (25 MPa).
    """
    return projection_mm * math.sqrt(3.0 * pressure_mpa / (phi * fy_mpa))


# --------------------------------------------------------------------------------------------
# Example E7.13 — slab base, axial load only
# --------------------------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class SlabBaseResult:
    """Outputs of an axial-only slab-base design (§7.9.2 / E7.13)."""

    bearing_resistance_mpa: float
    area_required_mm2: float
    projection_mm: float          # the effective-area projection ``a``
    thickness_raw_mm: float
    thickness_mm: float           # rounded up to a standard plate thickness
    plate_length_mm: float
    plate_width_mm: float
    clause: str = "Mahachi §7.9.2 / SANS 10100-1 cl. 3.5.3 — PROVISIONAL"


def design_slab_base_axial(
    *,
    axial_kn: float,
    fcu_mpa: float,
    section_depth_mm: float,
    section_width_mm: float,
    flange_thickness_mm: float,
    fy_mpa: float = 300.0,
) -> SlabBaseResult:
    """Design a slab base carrying axial load only (book Example E7.13).

    Uses the effective-area shape of Fig. 7.34: the bearing pressure is assumed uniform over an
    H-shaped effective area of projection ``a`` around the column, so
    ``A_eff(a) = 4a² + (4·b + 2·h − 2·tf)·a``. Equating to the required area ``N/Br`` and solving
    the quadratic gives ``a``; the plate thickness then follows from the 1 mm-strip flexure rule.
    """
    br = concrete_bearing_resistance_mpa(fcu_mpa)
    area_required = axial_kn * 1_000.0 / br                       # mm²

    # 4a² + (4b + 2h − 2tf)·a − A_req = 0  →  positive root.
    lin = 4.0 * section_width_mm + 2.0 * section_depth_mm - 2.0 * flange_thickness_mm
    disc = lin**2 + 4.0 * 4.0 * area_required
    a = (-lin + math.sqrt(disc)) / (2.0 * 4.0)

    t_raw = plate_thickness_from_pressure_mm(a, br, fy_mpa=fy_mpa)
    thickness = _round_up(t_raw, STANDARD_PLATE_THICKNESSES_MM)

    plate_length = _round_up(section_depth_mm + 2.0 * a, tuple(float(x) for x in range(0, 2001, 10)))
    plate_width = _round_up(section_width_mm + 2.0 * a, tuple(float(x) for x in range(0, 2001, 10)))

    return SlabBaseResult(
        bearing_resistance_mpa=br,
        area_required_mm2=area_required,
        projection_mm=a,
        thickness_raw_mm=t_raw,
        thickness_mm=thickness,
        plate_length_mm=plate_length,
        plate_width_mm=plate_width,
    )


# --------------------------------------------------------------------------------------------
# Example E7.14 — base subject to axial load AND moment
# --------------------------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class GussetCheck:
    """Gusset moment + shear resistance vs demand (cl. 13.5 / 13.4.1.1)."""

    moment_demand_knm: float
    moment_resistance_knm: float
    shear_demand_kn: float
    shear_resistance_kn: float

    @property
    def passes(self) -> bool:
        return (
            self.moment_demand_knm <= self.moment_resistance_knm
            and self.shear_demand_kn <= self.shear_resistance_kn
        )


@dataclasses.dataclass(frozen=True)
class WeldCheck:
    """Fillet-weld demand (kN/mm) + the smallest standard leg that resists it (cl. 13.13.2.2)."""

    demand_kn_per_mm: float
    leg_mm: float
    resistance_kn_per_mm: float


@dataclasses.dataclass(frozen=True)
class MomentBaseResult:
    """Outputs of an axial-plus-moment base design (§7.9.3 / E7.14)."""

    eccentricity_mm: float
    kern_d_over_6_mm: float
    tension_develops: bool
    bearing_resistance_mpa: float
    compression_depth_mm: float       # d2 — depth of the rectangular concrete stress block
    compression_force_kn: float       # Cu
    anchor_tension_kn: float           # Tu
    anchor_area_required_mm2: float    # An required for the holding-down bolts
    anchor_designation: str            # chosen standard bolt
    thickness_left_mm: float           # plate thickness, bolt-pull (tension) side
    thickness_right_mm: float          # plate thickness, concrete-bearing (compression) side
    thickness_mm: float                # rounded up to a standard plate thickness
    clause: str = "Mahachi §7.9.3 / SANS 10100-1 cl. 3.5.3 & 25.2.2.1 — PROVISIONAL"


def fillet_weld_resistance_kn_per_mm(leg_mm: float, *, xu_mpa: float = XU_E80XX_MPA) -> float:
    """Longitudinal fillet-weld factored resistance per mm of length (cl. 13.13.2.2, θ=0).

    Vr = 0.67·φw·Aw·Xu with throat Aw = 0.707·leg (per mm length). For a 14 mm E80XX fillet this
    gives ≈ 2.44 kN/mm and for 8 mm ≈ 1.40 kN/mm — the values the book uses in E7.14.
    """
    throat = _WELD_THROAT_FACTOR * leg_mm
    return _WELD_FORMULA_COEFF * PHI_WELD * throat * xu_mpa / 1_000.0


def select_fillet_weld(demand_kn_per_mm: float, *, xu_mpa: float = XU_E80XX_MPA) -> WeldCheck:
    """Smallest standard fillet leg whose resistance ≥ *demand_kn_per_mm*."""
    for leg in STANDARD_WELD_LEGS_MM:
        cap = fillet_weld_resistance_kn_per_mm(leg, xu_mpa=xu_mpa)
        if cap >= demand_kn_per_mm:
            return WeldCheck(demand_kn_per_mm, leg, cap)
    leg = STANDARD_WELD_LEGS_MM[-1]
    return WeldCheck(demand_kn_per_mm, leg, fillet_weld_resistance_kn_per_mm(leg, xu_mpa=xu_mpa))


def _select_anchor(area_required_mm2: float) -> str:
    """Smallest standard bolt whose tensile stress area ≥ *area_required_mm2*."""
    for designation, area in sorted(BOLT_STRESS_AREA_MM2.items(), key=lambda kv: kv[1]):
        if area >= area_required_mm2:
            return designation
    return max(BOLT_STRESS_AREA_MM2.items(), key=lambda kv: kv[1])[0]


def design_moment_base(
    *,
    axial_kn: float,
    moment_knm: float,
    base_length_mm: float,            # d — base length in the plane of the moment
    base_width_mm: float,             # b — base width
    bearing_width_mm: float,          # b used for the compression block (= base width; see note)
    fcu_mpa: float,
    pu_lever_mm: float,               # c — lever of the axial load about the tension bolts
    tension_bolt_to_comp_edge_mm: float,  # d1 — tension bolts → compression edge
    projection_mm: float,             # a — plate projection on the compression side
    n_tension_bolts: int,
    bolt_fu_mpa: float,
    bolt_inset_mm: float,             # l1 — tension bolt inset from the plate edge (≤ 70)
    bolt_to_gusset_face_mm: float,    # lever of the bolt pull about the gusset face
    section_depth_mm: float,          # h — column depth (for the gusset levers)
    fy_mpa: float = 300.0,
) -> MomentBaseResult:
    """Design a column base under axial load + moment (book Example E7.14).

    When the eccentricity ``e = M/N`` exceeds ``d/6`` the base develops tension on one side and
    the holding-down bolts take tension. Equilibrium (moments about the tension bolts) gives a
    rectangular concrete stress block of depth ``d2`` at stress Br; the bolt tension is then
    ``Tu = Cu − Pu``. The plate thickness is the larger of the bolt-pull side and the
    concrete-bearing side.
    """
    br = concrete_bearing_resistance_mpa(fcu_mpa)
    e = moment_knm * 1_000_000.0 / (axial_kn * 1_000.0)          # mm
    kern = base_length_mm / 6.0
    tension_develops = e > kern

    # Moments about the tension bolts:  Pu·c + Mu − Cu·(d1 − d2/2) = 0,  Cu = b·d2·Br
    #   → (b·Br/2)·d2² − (b·Br·d1)·d2 + (Pu·c + Mu) = 0   →  smaller positive root.
    applied = axial_kn * 1_000.0 * pu_lever_mm + moment_knm * 1_000_000.0   # N·mm
    qa = bearing_width_mm * br / 2.0
    qb = -bearing_width_mm * br * tension_bolt_to_comp_edge_mm
    qc = applied
    disc = qb**2 - 4.0 * qa * qc
    d2 = (-qb - math.sqrt(disc)) / (2.0 * qa)

    cu_kn = bearing_width_mm * d2 * br / 1_000.0
    tu_kn = cu_kn - axial_kn

    an_required = tu_kn * 1_000.0 / (n_tension_bolts * PHI_ANCHOR * bolt_fu_mpa)
    anchor = _select_anchor(an_required)

    # Plate thickness — bolt-pull (left) side: a concentrated bolt force over a dispersed width.
    le = bolt_inset_mm + bolt_to_gusset_face_mm / math.tan(math.radians(30.0))
    m_left = (tu_kn / n_tension_bolts) * bolt_to_gusset_face_mm * 1_000.0     # N·mm
    t_left = math.sqrt(m_left * 6.0 / (PHI_PLATE * fy_mpa * le))

    # Plate thickness — concrete-bearing (right) side: 1 mm strip under Br.
    t_right = plate_thickness_from_pressure_mm(projection_mm, br, fy_mpa=fy_mpa)

    thickness_raw = max(t_left, t_right, projection_mm / 5.0)
    thickness = _round_up(thickness_raw, STANDARD_PLATE_THICKNESSES_MM)

    return MomentBaseResult(
        eccentricity_mm=e,
        kern_d_over_6_mm=kern,
        tension_develops=tension_develops,
        bearing_resistance_mpa=br,
        compression_depth_mm=d2,
        compression_force_kn=cu_kn,
        anchor_tension_kn=tu_kn,
        anchor_area_required_mm2=an_required,
        anchor_designation=anchor,
        thickness_left_mm=t_left,
        thickness_right_mm=t_right,
        thickness_mm=thickness,
    )


def gusset_check(
    *,
    moment_demand_knm: float,
    shear_demand_kn: float,
    n_gussets: int,
    gusset_thickness_mm: float,
    gusset_depth_mm: float,
    fy_mpa: float = 300.0,
) -> GussetCheck:
    """Moment + shear resistance of the base gussets (cl. 13.5 / 13.4.1.1).

    Mr = n·φ·fy·(t·d²/6) (the book uses the elastic section modulus t·d²/6);
    Vr = n·0.66·φ·fy·(t·d).
    """
    z = gusset_thickness_mm * gusset_depth_mm**2 / 6.0
    mr = n_gussets * PHI_PLATE * fy_mpa * z / 1_000_000.0                       # kN·m
    av = gusset_thickness_mm * gusset_depth_mm
    vr = n_gussets * 0.66 * PHI_PLATE * fy_mpa * av / 1_000.0                   # kN
    return GussetCheck(moment_demand_knm, mr, shear_demand_kn, vr)
