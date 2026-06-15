"""Task 1.16 — column baseplate design (pinned + fixed).

PROVISIONAL module: tests pin the documented (simplified) formulas with hand-calcs.
The formulas require registered-engineer sign-off (standard PDFs absent from
`standards/`).

Run:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_baseplate.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.connections.bolts import make_bolt
from torenone_kernel.foundations.baseplate import (
    PHI_C,
    BasePlate,
    check_baseplate,
    design_baseplate,
)
from torenone_kernel.models.enums import SteelGrade
from torenone_kernel.models.results import BaseplateDesignResult

# column ~ UC 203×203
_COL = dict(column_depth_mm=203.0, column_flange_width_mm=203.0)


def _plate(thickness: float = 20.0, anchor_size: str = "M20") -> BasePlate:
    return BasePlate(
        length_mm=350.0, width_mm=350.0, thickness_mm=thickness,
        plate_fy_mpa=345.0, fc_mpa=25.0, anchor=make_bolt(anchor_size, "8.8"),
        n_anchors_total=4, n_anchors_tension=2, anchor_lever_mm=250.0,
        column_depth_mm=203.0, column_flange_width_mm=203.0,
    )


# ---------------------------------------------------------------------------
# 1. check_baseplate — limit states
# ---------------------------------------------------------------------------


class TestCheckBaseplate:
    def test_returns_four_checks(self):
        checks = check_baseplate(_plate(), base_fixity="pinned", axial_kn=200.0, shear_kn=50.0)
        assert len(checks) == 4
        names = {c.name for c in checks}
        assert names == {
            "baseplate: concrete bearing",
            "baseplate: plate bending",
            "baseplate: anchor tension",
            "baseplate: anchor shear",
        }

    def test_bearing_capacity_constant(self):
        # bearing cap = φc·0.85·f'c = 0.60·0.85·25 = 12.75 MPa (φc = 0.60, SANS cl. 13.1(j))
        assert PHI_C == 0.60
        cap = PHI_C * 0.85 * 25.0
        assert cap == pytest.approx(12.75)

    def test_pinned_bearing_utilisation_handcalc(self):
        # p = 200 kN / (350·350 = 122 500 mm²) = 1.6327 MPa; cap = 13.8125 -> util 0.1182
        checks = check_baseplate(_plate(), base_fixity="pinned", axial_kn=200.0, shear_kn=0.0)
        bearing = next(c for c in checks if c.name == "baseplate: concrete bearing")
        expected = (200_000.0 / 122_500.0) / (PHI_C * 0.85 * 25.0)
        assert bearing.utilisation == pytest.approx(expected, rel=1e-3)
        assert bearing.passed

    def test_pinned_no_anchor_tension(self):
        checks = check_baseplate(_plate(), base_fixity="pinned", axial_kn=200.0, shear_kn=40.0)
        tension = next(c for c in checks if c.name == "baseplate: anchor tension")
        assert tension.utilisation == pytest.approx(0.0)

    def test_anchor_shear_handcalc(self):
        # V = 60 kN / 4 anchors = 15 kN; anchor Vr(M20, φar=0.67, threads) = 73.38 -> util 0.2044
        checks = check_baseplate(_plate(), base_fixity="pinned", axial_kn=200.0, shear_kn=60.0)
        shear = next(c for c in checks if c.name == "baseplate: anchor shear")
        assert shear.utilisation == pytest.approx((60.0 / 4.0) / 73.38, rel=1e-3)

    def test_moment_increases_bearing_and_anchor_tension(self):
        pinned = check_baseplate(_plate(), base_fixity="pinned", axial_kn=200.0, shear_kn=0.0)
        fixed = check_baseplate(
            _plate(), base_fixity="fixed", axial_kn=200.0, shear_kn=0.0, moment_knm=40.0
        )
        b0 = next(c.utilisation for c in pinned if c.name == "baseplate: concrete bearing")
        b1 = next(c.utilisation for c in fixed if c.name == "baseplate: concrete bearing")
        t1 = next(c.utilisation for c in fixed if c.name == "baseplate: anchor tension")
        assert b1 > b0
        assert t1 > 0.0

    def test_uplift_creates_anchor_tension(self):
        # net uplift: axial = -100 kN (tension); 2 tension anchors M20 (φar=0.67) Tr=131.03 each
        checks = check_baseplate(_plate(), base_fixity="pinned", axial_kn=-100.0, shear_kn=0.0)
        tension = next(c for c in checks if c.name == "baseplate: anchor tension")
        assert tension.utilisation == pytest.approx(100.0 / (2.0 * 131.03), rel=1e-3)

    def test_huge_axial_fails_bearing(self):
        checks = check_baseplate(_plate(), base_fixity="pinned", axial_kn=5_000.0, shear_kn=0.0)
        bearing = next(c for c in checks if c.name == "baseplate: concrete bearing")
        assert not bearing.passed and bearing.utilisation > 1.0

    def test_clauses_provisional(self):
        for c in check_baseplate(_plate(), base_fixity="pinned", axial_kn=200.0, shear_kn=40.0):
            assert "PROVISIONAL" in c.clause


# ---------------------------------------------------------------------------
# 2. design_baseplate — auto-selection
# ---------------------------------------------------------------------------


class TestDesignBaseplate:
    def test_pinned_passes(self):
        r = design_baseplate(
            base_fixity="pinned", axial_kn=120.0, shear_kn=15.0, moment_knm=0.0,
            steel_grade=SteelGrade.S355JR, **_COL,
        )
        assert isinstance(r, BaseplateDesignResult)
        assert r.base_fixity == "pinned"
        assert r.passed
        assert r.max_utilisation <= 1.0
        assert "mm plate" in r.description

    def test_fixed_with_moment_passes(self):
        r = design_baseplate(
            base_fixity="fixed", axial_kn=120.0, shear_kn=20.0, moment_knm=60.0,
            steel_grade=SteelGrade.S355JR, **_COL,
        )
        assert r.base_fixity == "fixed"
        assert r.passed

    def test_unsatisfiable_returns_failing_strongest(self):
        r = design_baseplate(
            base_fixity="fixed", axial_kn=50_000.0, shear_kn=5_000.0, moment_knm=5_000.0,
            steel_grade=SteelGrade.S355JR, **_COL,
        )
        assert not r.passed
        assert "M30" in r.description

    def test_deterministic(self):
        kwargs = dict(
            base_fixity="pinned", axial_kn=120.0, shear_kn=15.0, moment_knm=0.0,
            steel_grade=SteelGrade.S355JR, **_COL,
        )
        a = design_baseplate(**kwargs)
        b = design_baseplate(**kwargs)
        assert a.model_dump(mode="json") == b.model_dump(mode="json")

    def test_aggregates_pass_and_utilisation(self):
        r = design_baseplate(
            base_fixity="pinned", axial_kn=120.0, shear_kn=15.0, moment_knm=0.0,
            steel_grade=SteelGrade.S355JR, **_COL,
        )
        assert r.passed == all(c.passed for c in r.checks)
        assert r.max_utilisation == pytest.approx(max(c.utilisation for c in r.checks))
