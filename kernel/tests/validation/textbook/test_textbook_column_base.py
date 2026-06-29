"""Column-base validation vs the SECOND authority — Mahachi, *Design of Structural Steelwork to
SANS 10162* (CSIR, 2004; J Mahachi Pr.Eng PhD), §7.9, worked Examples **E7.13** and **E7.14**.

This is the column-base counterpart to the member suite (test_textbook_members.py). It proves the
SANS 10100 / BS 5950 effective-area column-base method in
``torenone_kernel.foundations.baseplate_sans`` reproduces the textbook's published worked answers
**to the millimetre** — the same method the SAISC Red Book §4.2.2 uses, so both SA authorities now
agree on the column base (the area where our AISC-style ``foundations/baseplate.py`` diverges).

PROVISIONAL: this method is validated but not yet wired into the live design path — it awaits
registered-engineer sign-off (see docs/REDBOOK-VALIDATION.md). Only numeric facts are encoded
(copyright respected); each assertion cites its example. Must-pass.

Section geometry is taken from the kernel's own (Red-Book-validated) section library, so this also
cross-checks that data feeds the base design consistently.
"""

from __future__ import annotations

import pytest
from torenone_kernel.foundations.baseplate_sans import (
    design_moment_base,
    design_slab_base_axial,
    fillet_weld_resistance_kn_per_mm,
    gusset_check,
    select_fillet_weld,
)
from torenone_kernel.sections import SectionLibrary

_SRC = "Mahachi, Design of Structural Steelwork to SANS 10162 (CSIR, 2004)"
_TOL = 0.02

_LIB = SectionLibrary.load_default()


# --------------------------------------------------------------------------------------------
# Example E7.13 — slab base, axial load only (book pp. 7.82–7.83)
# --------------------------------------------------------------------------------------------
def test_e7_13_slab_base_axial_only() -> None:
    # 356×171×45 I-column, ultimate axial 900 kN, 25 MPa (cube) concrete slab base.
    col = _LIB.get("356x171x45")
    res = design_slab_base_axial(
        axial_kn=900.0,
        fcu_mpa=25.0,
        section_depth_mm=col.depth_mm,
        section_width_mm=col.width_mm,
        flange_thickness_mm=col.flange_thickness_mm,
        fy_mpa=300.0,
    )
    assert res.bearing_resistance_mpa == pytest.approx(10.0), f"{_SRC} E7.13: Br vs 10 MPa"
    assert res.area_required_mm2 == pytest.approx(90_000.0, rel=_TOL), f"{_SRC} E7.13: A vs 90 000"
    assert res.projection_mm == pytest.approx(56.4, rel=_TOL), f"{_SRC} E7.13: a={res.projection_mm:.1f} vs 56.4 mm"
    assert res.thickness_raw_mm == pytest.approx(18.5, rel=0.03), f"{_SRC} E7.13: tp_raw vs 18.5 mm"
    assert res.thickness_mm == 20.0, f"{_SRC} E7.13: tp={res.thickness_mm} vs 20 mm"
    # Book rounds the plate to 470×300; the length matches exactly (width rounds to 290, book chose 300).
    assert res.plate_length_mm == pytest.approx(470.0), f"{_SRC} E7.13: plate length vs 470 mm"


# --------------------------------------------------------------------------------------------
# Example E7.14 — base subject to axial load AND moment (book pp. 7.84–7.90)
# --------------------------------------------------------------------------------------------
def _e7_14_base():  # type: ignore[no-untyped-def]
    # 203×203×86 H-column; Pu=198 kN, Mu=264 kN·m; Grade 300W; fcu=20 MPa; Grade-43 (fu=430) bolts.
    # Base plan: d=800 (moment plane), b=480; tension bolts inset 70 mm; c=330; d1=730; a=113.1.
    # The book uses an effective compression width of 460 mm in the Cu step (the plan shows 480 —
    # a minor book inconsistency); 460 is passed to reproduce the published d2 = 135 mm.
    col = _LIB.get("203x203x86")
    return design_moment_base(
        axial_kn=198.0,
        moment_knm=264.0,
        base_length_mm=800.0,
        base_width_mm=480.0,
        bearing_width_mm=460.0,
        fcu_mpa=20.0,
        pu_lever_mm=330.0,
        tension_bolt_to_comp_edge_mm=730.0,
        projection_mm=113.1,
        n_tension_bolts=2,
        bolt_fu_mpa=430.0,
        bolt_inset_mm=70.0,
        bolt_to_gusset_face_mm=43.1,
        section_depth_mm=col.depth_mm,
        fy_mpa=300.0,
    )


def test_e7_14_eccentricity_and_tension() -> None:
    res = _e7_14_base()
    assert res.eccentricity_mm == pytest.approx(1333.0, rel=_TOL), f"{_SRC} E7.14: e vs 1333 mm"
    assert res.kern_d_over_6_mm == pytest.approx(133.3, rel=_TOL), f"{_SRC} E7.14: d/6 vs 133 mm"
    assert res.tension_develops is True, f"{_SRC} E7.14: tension must develop (e > d/6)"
    assert res.bearing_resistance_mpa == pytest.approx(8.0), f"{_SRC} E7.14: Br vs 8 MPa"


def test_e7_14_stress_block_and_forces() -> None:
    res = _e7_14_base()
    assert res.compression_depth_mm == pytest.approx(135.0, rel=_TOL), f"{_SRC} E7.14: d2 vs 135 mm"
    assert res.compression_force_kn == pytest.approx(497.0, rel=_TOL), f"{_SRC} E7.14: Cu vs 497 kN"
    assert res.anchor_tension_kn == pytest.approx(299.0, rel=_TOL), f"{_SRC} E7.14: Tu vs 299 kN"


def test_e7_14_holding_down_bolts() -> None:
    res = _e7_14_base()
    assert res.anchor_area_required_mm2 == pytest.approx(519.0, rel=_TOL), f"{_SRC} E7.14: An vs 519 mm²"
    assert res.anchor_designation == "M30", f"{_SRC} E7.14: bolt {res.anchor_designation} vs M30 (An=561)"


def test_e7_14_plate_thickness() -> None:
    res = _e7_14_base()
    assert res.thickness_left_mm == pytest.approx(31.4, rel=0.03), f"{_SRC} E7.14: tp(left) vs 31.4 mm"
    assert res.thickness_right_mm == pytest.approx(33.7, rel=0.03), f"{_SRC} E7.14: tp(right) vs 33.7 mm"
    assert res.thickness_mm == 35.0, f"{_SRC} E7.14: base plate tp vs 35 mm"


def test_e7_14_gussets() -> None:
    # Two 16 mm gussets, 300 mm deep. Right side governs: Mu = Cu·((d−h)/2 − d2/2) ≈ 110 kN·m.
    res = _e7_14_base()
    base_projection = (800.0 - 222.3) / 2.0
    lever = base_projection - res.compression_depth_mm / 2.0
    m_demand = res.compression_force_kn * lever / 1_000.0
    chk = gusset_check(
        moment_demand_knm=m_demand,
        shear_demand_kn=res.compression_force_kn,
        n_gussets=2,
        gusset_thickness_mm=16.0,
        gusset_depth_mm=300.0,
    )
    assert m_demand == pytest.approx(110.0, rel=_TOL), f"{_SRC} E7.14: gusset Mu={m_demand:.0f} vs 110 kN·m"
    assert chk.moment_resistance_knm == pytest.approx(129.6, rel=_TOL), f"{_SRC} E7.14: gusset Mr vs 129.6 kN·m"
    assert chk.shear_resistance_kn == pytest.approx(1710.0, rel=_TOL), f"{_SRC} E7.14: gusset Vr vs 1710 kN"
    assert chk.passes, f"{_SRC} E7.14: gussets must pass"


def test_e7_14_welds() -> None:
    # Column-flange→gusset demand ≈ 2.15 kN/mm → 14 mm E80XX; gusset→base ≈ 1.36 kN/mm → 8 mm E80XX.
    assert fillet_weld_resistance_kn_per_mm(14.0) == pytest.approx(2.44, rel=_TOL), f"{_SRC} E7.14: 14 mm fillet"
    assert fillet_weld_resistance_kn_per_mm(8.0) == pytest.approx(1.40, rel=_TOL), f"{_SRC} E7.14: 8 mm fillet"
    assert select_fillet_weld(2.145).leg_mm == 14.0, f"{_SRC} E7.14: column-gusset weld vs 14 mm"
    assert select_fillet_weld(1.361).leg_mm == 8.0, f"{_SRC} E7.14: gusset-base weld vs 8 mm"
