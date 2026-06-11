"""Task 1.17 — concrete pad footing design (SANS 10100-1).

⚠️ PROVISIONAL concrete module (different standard than the steel kernel). Tests pin the
documented (simplified, BS 8110-lineage) formulas with hand-calcs; the formulas
themselves require registered-engineer sign-off (standard PDFs absent from `standards/`).

Run:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_pad_footing.py -q
"""

from __future__ import annotations

import math

import pytest
from torenone_kernel.foundations.pad_footing import (
    GAMMA_CONCRETE_KN_M3,
    PadFooting,
    check_pad_footing,
    design_pad_footing,
)
from torenone_kernel.models.results import PadFootingDesignResult


def _footing(plan: float = 1000.0, thickness: float = 400.0,
             bar: float = 16.0, spacing: float = 200.0) -> PadFooting:
    return PadFooting(
        plan_size_mm=plan, thickness_mm=thickness, cover_mm=50.0,
        bar_diameter_mm=bar, bar_spacing_mm=spacing,
        fcu_mpa=25.0, fy_rebar_mpa=450.0, column_size_mm=350.0,
    )


# ---------------------------------------------------------------------------
# 1. check_pad_footing — limit states
# ---------------------------------------------------------------------------


class TestCheckPadFooting:
    def test_returns_four_checks(self):
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        assert {c.name for c in checks} == {
            "footing: soil bearing",
            "footing: punching shear",
            "footing: one-way shear",
            "footing: flexure / reinforcement",
        }

    def test_bearing_handcalc(self):
        # 1.0 m² pad, D=0.4 m -> self-wt = 1·0.4·24 = 9.6 kN
        # gross = (100 + 9.6)/1.0 = 109.6 kPa; allowable 150 -> util 0.7307
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        bearing = next(c for c in checks if c.name == "footing: soil bearing")
        self_wt = 1.0 * 0.4 * GAMMA_CONCRETE_KN_M3
        expected = ((100.0 + self_wt) / 1.0) / 150.0
        assert bearing.utilisation == pytest.approx(expected, rel=1e-3)
        assert bearing.passed

    def test_punching_handcalc(self):
        # d = 400 - 50 - 16/2 = 342 mm; perimeter = 4·350 = 1400 mm
        # v = 140 000 / (1400·342) = 0.2924 MPa; v_max = 0.75·√25 = 3.75 -> util 0.078
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        punch = next(c for c in checks if c.name == "footing: punching shear")
        d_mm = 400.0 - 50.0 - 8.0
        v_applied = 140_000.0 / (1400.0 * d_mm)
        assert punch.utilisation == pytest.approx(v_applied / 3.75, rel=1e-3)

    def test_lower_allowable_pressure_raises_bearing_util(self):
        common = dict(service_axial_kn=100.0, factored_axial_kn=140.0)
        high = check_pad_footing(_footing(), allowable_bearing_kpa=300.0, **common)
        low = check_pad_footing(_footing(), allowable_bearing_kpa=120.0, **common)
        ub_high = next(c.utilisation for c in high if c.name == "footing: soil bearing")
        ub_low = next(c.utilisation for c in low if c.name == "footing: soil bearing")
        assert ub_low > ub_high

    def test_more_reinforcement_lowers_flexure_util(self):
        common = dict(service_axial_kn=300.0, factored_axial_kn=420.0, allowable_bearing_kpa=200.0)
        light = check_pad_footing(_footing(bar=12.0, spacing=200.0), **common)
        heavy = check_pad_footing(_footing(bar=20.0, spacing=100.0), **common)
        f_light = next(c.utilisation for c in light if c.name == "footing: flexure / reinforcement")
        f_heavy = next(c.utilisation for c in heavy if c.name == "footing: flexure / reinforcement")
        assert f_heavy < f_light

    def test_undersized_pad_fails_bearing(self):
        checks = check_pad_footing(
            _footing(plan=600.0), service_axial_kn=2_000.0, factored_axial_kn=2_800.0,
            allowable_bearing_kpa=150.0,
        )
        bearing = next(c for c in checks if c.name == "footing: soil bearing")
        assert not bearing.passed and bearing.utilisation > 1.0

    def test_clauses_cite_sans_10100_and_provisional(self):
        for c in check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        ):
            assert "SANS 10100-1" in c.clause
            assert "PROVISIONAL" in c.clause


# ---------------------------------------------------------------------------
# 2. design_pad_footing — auto-selection
# ---------------------------------------------------------------------------


class TestDesignPadFooting:
    def test_passes_for_typical_base(self):
        r = design_pad_footing(
            service_axial_kn=120.0, factored_axial_kn=170.0, allowable_bearing_kpa=150.0,
            column_size_mm=350.0,
        )
        assert isinstance(r, PadFootingDesignResult)
        assert r.passed
        assert r.max_utilisation <= 1.0
        assert r.plan_size_mm % 50.0 == 0.0
        assert r.thickness_mm in (300.0, 400.0, 500.0, 600.0, 750.0, 900.0)
        assert "square" in r.description

    def test_plan_area_satisfies_bearing(self):
        service, allowable = 150.0, 120.0
        r = design_pad_footing(
            service_axial_kn=service, factored_axial_kn=210.0,
            allowable_bearing_kpa=allowable, column_size_mm=350.0,
        )
        # plan must at least cover the pure bearing demand area
        assert (r.plan_size_mm / 1_000.0) ** 2 >= service / allowable

    def test_weaker_soil_gives_larger_pad(self):
        strong = design_pad_footing(
            service_axial_kn=150.0, factored_axial_kn=210.0, allowable_bearing_kpa=300.0,
            column_size_mm=350.0,
        )
        weak = design_pad_footing(
            service_axial_kn=150.0, factored_axial_kn=210.0, allowable_bearing_kpa=100.0,
            column_size_mm=350.0,
        )
        assert weak.plan_size_mm > strong.plan_size_mm

    def test_unsatisfiable_returns_failing_strongest(self):
        r = design_pad_footing(
            service_axial_kn=200.0, factored_axial_kn=50_000.0, allowable_bearing_kpa=150.0,
            column_size_mm=350.0,
        )
        assert not r.passed
        assert r.thickness_mm == 900.0   # thickest tried

    def test_deterministic(self):
        kwargs = dict(
            service_axial_kn=120.0, factored_axial_kn=170.0, allowable_bearing_kpa=150.0,
            column_size_mm=350.0,
        )
        a = design_pad_footing(**kwargs)
        b = design_pad_footing(**kwargs)
        assert a.model_dump(mode="json") == b.model_dump(mode="json")

    def test_aggregates_pass_and_utilisation(self):
        r = design_pad_footing(
            service_axial_kn=120.0, factored_axial_kn=170.0, allowable_bearing_kpa=150.0,
            column_size_mm=350.0,
        )
        assert r.passed == all(c.passed for c in r.checks)
        assert r.max_utilisation == pytest.approx(max(c.utilisation for c in r.checks))

    def test_provided_steel_area_formula(self):
        # Y16@200 both ways: bars/m = 5, area = π/4·16² = 201.06 -> 1005.3 mm²/m
        footing = _footing(bar=16.0, spacing=200.0)
        from torenone_kernel.foundations.pad_footing import _provided_steel_area_mm2_per_m
        expected = (1_000.0 / 200.0) * (math.pi / 4.0 * 16.0**2)
        assert _provided_steel_area_mm2_per_m(footing) == pytest.approx(expected)
