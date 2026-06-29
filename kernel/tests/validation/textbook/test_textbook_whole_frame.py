"""Whole-frame benchmark vs the SECOND authority — Mahachi, *Design of Structural Steelwork to
SANS 10162* (CSIR 2004), worked Example **E13.1, "Design of an industrial building"** (Chapter 13).

E13.1 is a COMPLETE worked single-bay portal frame: 24 m span, 6 m eaves, 10° pitch, 5 m bay,
hinged bases, haunched eaves/ridge, 305×165×46 columns + 305×102×33 rafters, Grade 300W. The book
gives the geometry, loads, load combinations, the frame-analysis member forces, and the full member
design. This is the closest thing to the "whole-frame validation gate" available from a published
authority (see docs/SIGN-OFF-PACK.md Part 4).

This suite validates the **member-design half** of that benchmark: fed the book's analysis member
forces, our member-design path reproduces the book's column design. The **analysis half** (does our
frame model reproduce the book's member forces?) is a separate, larger step — the book uses a
*haunched* frame + *second-order* analysis, which our prismatic model approximates; that comparison
is tracked in docs/SIGN-OFF-PACK.md Part 4.

The gravity ULS combination (LC5 = 1.2·permanent + 1.6·imposed) uses the SAME load factors in the
1989 code the book predates AND the current SANS 10160-1:2011 — so the gravity path is directly
comparable (wind is handled separately; the book's wind is the superseded 1989 code).

Only numeric facts are encoded; must-pass.
"""

from __future__ import annotations

import math

import pytest
from torenone_kernel.analysis.plane_frame import PortalAnalysis
from torenone_kernel.checks.axial import cr_flexural
from torenone_kernel.checks.bending import mcr_elastic, mr_laterally_supported, mr_ltb, omega2_factor
from torenone_kernel.checks.classification import SectionClass
from torenone_kernel.checks.interaction import beam_column_check
from torenone_kernel.models.enums import SteelGrade, TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FoundationInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    Materials,
    Restraints,
    WindContext,
)
from torenone_kernel.sections import SectionLibrary

_SRC = "Mahachi, Design of Structural Steelwork to SANS 10162 (CSIR, 2004), E13.1"
_FY = 300.0  # Grade 300W

_LIB = SectionLibrary.load_default()
_COL = _LIB.get("305x165x46")  # the E13.1 column

# Column member forces from the book's analysis, gravity ULS (LC5 = 1.2D + 1.6L), at the eaves.
_CU_KN = 49.7      # axial compression
_MU_KNM = 150.1    # eaves moment
_KAPPA = -50.7 / 150.1  # moment-gradient ratio for the column segment (nodes 16–18)


def test_e13_1_section_data_is_the_book_section() -> None:
    # The kernel's section library reproduces the book's 305×165×46 properties.
    assert _COL.area_mm2 == pytest.approx(5880.0, rel=0.01), f"{_SRC}: A vs 5880 mm²"
    assert _COL.plastic_modulus_zx_mm3 == pytest.approx(722e3, rel=0.01), f"{_SRC}: Zplx vs 722e3"
    assert _COL.radius_gyration_rx_mm == pytest.approx(130.0, rel=0.01), f"{_SRC}: rx vs 130 mm"
    assert _COL.radius_gyration_ry_mm == pytest.approx(39.0, rel=0.01), f"{_SRC}: ry vs 39 mm"


def test_e13_1_column_resistances() -> None:
    cr_xsec = 0.9 * _COL.area_mm2 * _FY / 1000.0                      # λ = 0
    cr_overall = cr_flexural(_COL.area_mm2, _FY, 6000.0, _COL.radius_gyration_rx_mm)
    mrx = mr_laterally_supported(
        SectionClass.CLASS1, _COL.plastic_modulus_zx_mm3, _COL.elastic_modulus_sx_mm3, _FY
    )
    assert cr_xsec == pytest.approx(1588.0, rel=0.01), f"{_SRC}: Cr(λ=0) vs 1588 kN"
    assert cr_overall == pytest.approx(1368.0, rel=0.01), f"{_SRC}: Cr(overall) vs 1368 kN"
    assert mrx == pytest.approx(195.0, rel=0.01), f"{_SRC}: Mrx vs 195 kN·m"


def test_e13_1_column_cross_sectional_strength() -> None:
    # (i) Cross-sectional strength: Cu/Cr + 0.85·U1·Mu/Mrx, U1=1.0 → 0.686.
    cr_xsec = 0.9 * _COL.area_mm2 * _FY / 1000.0
    mrx = mr_laterally_supported(
        SectionClass.CLASS1, _COL.plastic_modulus_zx_mm3, _COL.elastic_modulus_sx_mm3, _FY
    )
    chk = beam_column_check(_CU_KN, cr_xsec, _MU_KNM, mrx, 1.0, SectionClass.CLASS1)
    assert chk.utilisation == pytest.approx(0.686, rel=0.01), f"{_SRC}: x-sec interaction vs 0.686"


def test_e13_1_column_overall_member_strength() -> None:
    # (ii) Overall member strength: Cr(KLx=6 m), U1=0.742 → 0.522.
    cr_overall = cr_flexural(_COL.area_mm2, _FY, 6000.0, _COL.radius_gyration_rx_mm)
    mrx = mr_laterally_supported(
        SectionClass.CLASS1, _COL.plastic_modulus_zx_mm3, _COL.elastic_modulus_sx_mm3, _FY
    )
    chk = beam_column_check(_CU_KN, cr_overall, _MU_KNM, mrx, 0.742, SectionClass.CLASS1)
    assert chk.utilisation == pytest.approx(0.522, rel=0.01), f"{_SRC}: overall interaction vs 0.522"


def test_e13_1_column_lateral_torsional_buckling() -> None:
    # (iii) LTB: ω2 from κ=-0.338, Mcr, LTB-reduced Mrx, interaction with the book's Cr=1056 kN
    # (torsional-flexural — the book's E_z path; our cr_flexural covers flexural buckling only).
    w2 = omega2_factor(_KAPPA)
    assert w2 == pytest.approx(1.43, rel=0.02), f"{_SRC}: ω2 vs 1.43"
    mcr = mcr_elastic(
        4000.0, _COL.second_moment_iy_mm4, _COL.torsion_constant_j_mm4,
        _COL.warping_constant_cw_mm6, w2,
    )
    mrl = mr_ltb(
        SectionClass.CLASS1, _COL.plastic_modulus_zx_mm3, _COL.elastic_modulus_sx_mm3, _FY, mcr
    )
    # Our Mcr per the published formula is ~305 kN·m vs the book's 331; the LTB-reduced Mrx is
    # ~180 vs 183 (≤2%, on the conservative side), so the interaction lands at ~0.757 vs 0.743.
    chk = beam_column_check(_CU_KN, 1056.0, _MU_KNM, mrl, 1.0, SectionClass.CLASS1)
    assert mrl == pytest.approx(183.2, rel=0.03), f"{_SRC}: LTB-reduced Mrx vs 183 kN·m"
    assert chk.utilisation == pytest.approx(0.743, rel=0.03), f"{_SRC}: LTB interaction vs 0.743"


# ---------------------------------------------------------------------------------------------
# Analysis half — does OUR frame model reproduce the book's member forces under gravity?
# ---------------------------------------------------------------------------------------------
def _e13_1_gravity_analysis():  # type: ignore[no-untyped-def]
    """Run E13.1's frame through the kernel's PyNite portal model under the gravity ULS (LC5).

    The applied rafter UDL is calibrated to the book's own stated load totals so the comparison
    isolates the *analysis model* (not the load magnitudes):
      roof permanent (nodes 4–16) = 17.92 kN  +  rafter steel self-weight 2×12.185×0.33 = 8.04 kN
      roof imposed = 36.6 kN   →   LC5 = 1.2·(17.92+8.04) + 1.6·36.6 = 89.7 kN over both rafters.
    """
    col = _LIB.get("305x165x46")
    raf = _LIB.get("305x102x33")
    geom = FrameGeometry(
        span_m=24.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=5.0, number_of_bays=10
    )
    spec = FrameSpec(
        geometry=geom,
        materials=Materials(steel_grade=SteelGrade.S355JR),
        restraints=Restraints(rafter_restraint_spacing_m=2.0, column_restraint_spacing_m=2.0),
        dead=DeadLoadInputs(roof_kpa=0.079, services_kpa=0.05),
        imposed=ImposedLoadInputs(roof_access=False),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.C),
        foundation=FoundationInputs(),
    )
    rafter_len_m = math.hypot(12.0, geom.apex_height_m - 6.0)
    lc5_total_kn = 1.2 * (17.92 + 8.04) + 1.6 * 36.6
    udl = lc5_total_kn / (2.0 * rafter_len_m)
    return PortalAnalysis(spec, col, raf).run("LC5_gravity", rafter_udl_kn_per_m=udl)


def test_e13_1_analysis_eaves_moment_corroborates_book() -> None:
    # Our PRISMATIC, linear model reproduces the book's eaves moment (150.1 kN·m) within ~6%.
    # We land at ≈141 — the book's *haunch* stiffens the eaves and attracts the extra moment, and
    # the book uses second-order analysis; both are small for this stiff portal. A corroboration of
    # the analysis engine on a published whole frame, with the prismatic simplification quantified.
    res = _e13_1_gravity_analysis()
    eaves = next(f for f in res.forces if f.location == "eaves_L")
    assert eaves.moment_knm == pytest.approx(150.1, rel=0.10), (
        f"{_SRC}: eaves moment {eaves.moment_knm:.1f} vs book 150.1 kN·m (prismatic vs haunched)"
    )


def test_e13_1_analysis_is_symmetric_and_pinned() -> None:
    # Gravity load on a symmetric frame → equal eaves moments, ~zero moment at the pinned bases.
    res = _e13_1_gravity_analysis()
    by = {f.location: f for f in res.forces}
    assert by["eaves_L"].moment_knm == pytest.approx(by["eaves_R"].moment_knm, rel=1e-3), "symmetry"
    assert abs(by["col_base_L"].moment_knm) < 1.0, "pinned base → ~0 moment"
    assert abs(by["col_base_R"].moment_knm) < 1.0, "pinned base → ~0 moment"
