"""Task 1.17 — concrete pad footing design (SANS 10100-1 / SABS 0100-1 Ed. 2.2).

Verified against the standard (PDF in `standards/`): flexure K/z/As (cl. 4.3.3.4),
design concrete shear stress vc (cl. 4.3.4 eq. 2), max shear v_max (cl. 4.3.4.1),
bending critical section at the column face (cl. 4.10.2.2), min reinforcement
(cl. 4.11.4). Tests pin the standard formulas with hand-calcs.

Run:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_pad_footing.py -q
"""

from __future__ import annotations

import math

import pytest
from torenone_kernel.foundations.pad_footing import (
    GAMMA_CONCRETE_KN_M3,
    K_PRIME,
    PadFooting,
    check_pad_footing,
    design_concrete_shear_stress_vc,
    design_pad_footing,
    max_shear_stress_vmax,
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
# 1. SANS 10100-1 material formulas (pinned to the standard)
# ---------------------------------------------------------------------------


class TestSansFormulas:
    def test_k_prime_is_standard(self):
        assert K_PRIME == 0.156   # cl. 4.3.3.4

    def test_vmax_fcu25(self):
        # cl. 4.3.4.1: v_max = min(0.75·√25, 4.75) = min(3.75, 4.75) = 3.75
        assert max_shear_stress_vmax(25.0) == pytest.approx(3.75)

    def test_vmax_capped_at_4p75(self):
        # 0.75·√50 = 5.30 -> capped at 4.75
        assert max_shear_stress_vmax(50.0) == pytest.approx(4.75)

    def test_vc_matches_eq2(self):
        # vc = (0.75/1.4)·(fcu/25)^⅓·(100As/bd)^⅓·(400/d)^¼
        fcu, as_per_m, d = 25.0, 1005.31, 342.0
        rho = min(100.0 * as_per_m / (1_000.0 * d), 3.0)
        expected = (0.75 / 1.4) * (fcu / 25.0) ** (1 / 3) * rho ** (1 / 3) * (400.0 / d) ** 0.25
        assert design_concrete_shear_stress_vc(fcu, as_per_m, d) == pytest.approx(expected)

    def test_vc_rho_capped_at_3(self):
        # huge As -> (100As/bd) capped at 3
        d = 300.0
        big = design_concrete_shear_stress_vc(25.0, 1_000_000.0, d)
        at_cap = (0.75 / 1.4) * 1.0 * 3.0 ** (1 / 3) * (400.0 / d) ** 0.25
        assert big == pytest.approx(at_cap)


# ---------------------------------------------------------------------------
# 2. check_pad_footing — limit states
# ---------------------------------------------------------------------------


class TestCheckPadFooting:
    def test_returns_five_checks(self):
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        assert {c.name for c in checks} == {
            "footing: soil bearing",
            "footing: max shear at column face",
            "footing: punching shear (1.5d)",
            "footing: one-way shear",
            "footing: flexure / reinforcement",
        }

    def test_bearing_handcalc(self):
        # 1.0 m² pad, D=0.4 m -> self-wt = 9.6 kN; gross = 109.6 kPa; /150 -> 0.7307
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        bearing = next(c for c in checks if c.name == "footing: soil bearing")
        self_wt = 1.0 * 0.4 * GAMMA_CONCRETE_KN_M3
        assert bearing.utilisation == pytest.approx(((100.0 + self_wt) / 1.0) / 150.0, rel=1e-3)
        assert bearing.passed

    def test_max_face_shear_handcalc(self):
        # d = 342 mm; v_face = 140 000 / (4·350·342) = 0.2924 MPa; v_max = 3.75 -> 0.078
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        face = next(c for c in checks if c.name == "footing: max shear at column face")
        v_face = 140_000.0 / (4.0 * 350.0 * 342.0)
        assert face.utilisation == pytest.approx(v_face / 3.75, rel=1e-3)

    def test_one_way_shear_uses_vc(self):
        # wide footing so the d-from-face section lies within the pad
        f = _footing(plan=2000.0, thickness=400.0)
        checks = check_pad_footing(
            f, service_axial_kn=200.0, factored_axial_kn=300.0, allowable_bearing_kpa=150.0,
        )
        oneway = next(c for c in checks if c.name == "footing: one-way shear")
        d = 400.0 - 50.0 - 8.0
        as_prov = (1_000.0 / 200.0) * (math.pi / 4.0 * 16.0**2)
        vc = design_concrete_shear_stress_vc(25.0, as_prov, d)
        proj = (2.0 - 0.35) / 2.0
        av = proj - d / 1_000.0
        v = (300.0 / 4.0) * 2.0 * av * 1_000.0 / (2000.0 * d)
        assert oneway.utilisation == pytest.approx(v / vc, rel=1e-3)

    def test_min_reinforcement_floor_governs_for_light_load(self):
        # tiny moment -> As governed by cl. 4.11.4 minimum 0.13 % of gross
        f = _footing(plan=1000.0, thickness=300.0, bar=12.0, spacing=200.0)
        checks = check_pad_footing(
            f, service_axial_kn=50.0, factored_axial_kn=70.0, allowable_bearing_kpa=200.0,
        )
        flex = next(c for c in checks if c.name == "footing: flexure / reinforcement")
        as_min = 0.0013 * 1_000.0 * 300.0
        as_prov = (1_000.0 / 200.0) * (math.pi / 4.0 * 12.0**2)
        assert flex.utilisation == pytest.approx(as_min / as_prov, rel=1e-3)

    def test_more_reinforcement_lowers_flexure_util(self):
        common = dict(service_axial_kn=300.0, factored_axial_kn=420.0, allowable_bearing_kpa=200.0)
        light = check_pad_footing(_footing(bar=12.0, spacing=200.0), **common)
        heavy = check_pad_footing(_footing(bar=20.0, spacing=100.0), **common)
        f_light = next(c.utilisation for c in light if c.name == "footing: flexure / reinforcement")
        f_heavy = next(c.utilisation for c in heavy if c.name == "footing: flexure / reinforcement")
        assert f_heavy < f_light

    def test_lower_allowable_pressure_raises_bearing_util(self):
        common = dict(service_axial_kn=100.0, factored_axial_kn=140.0)
        high = check_pad_footing(_footing(), allowable_bearing_kpa=300.0, **common)
        low = check_pad_footing(_footing(), allowable_bearing_kpa=120.0, **common)
        ub_high = next(c.utilisation for c in high if c.name == "footing: soil bearing")
        ub_low = next(c.utilisation for c in low if c.name == "footing: soil bearing")
        assert ub_low > ub_high

    def test_undersized_pad_fails_bearing(self):
        checks = check_pad_footing(
            _footing(plan=600.0), service_axial_kn=2_000.0, factored_axial_kn=2_800.0,
            allowable_bearing_kpa=150.0,
        )
        bearing = next(c for c in checks if c.name == "footing: soil bearing")
        assert not bearing.passed and bearing.utilisation > 1.0

    def test_structural_checks_cite_sans_10100(self):
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        for c in checks:
            if c.name == "footing: soil bearing":
                assert "Geotechnical" in c.clause          # engineer-supplied allowable
            else:
                assert "SANS 10100-1" in c.clause           # verified concrete clauses

    def test_no_provisional_flag_remaining(self):
        # SANS 10100-1 is now available -> concrete checks are no longer PROVISIONAL
        checks = check_pad_footing(
            _footing(), service_axial_kn=100.0, factored_axial_kn=140.0,
            allowable_bearing_kpa=150.0,
        )
        assert all("PROVISIONAL" not in c.clause for c in checks)


# ---------------------------------------------------------------------------
# 3. design_pad_footing — auto-selection
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
        assert r.thickness_mm == 900.0

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
        footing = _footing(bar=16.0, spacing=200.0)
        from torenone_kernel.foundations.pad_footing import _provided_steel_area_mm2_per_m
        expected = (1_000.0 / 200.0) * (math.pi / 4.0 * 16.0**2)
        assert _provided_steel_area_mm2_per_m(footing) == pytest.approx(expected)
