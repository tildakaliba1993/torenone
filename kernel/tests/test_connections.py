"""Task 1.15 — portal-frame connection design (eaves + apex).

PROVISIONAL module: tests pin the SANS 10162-1 formulas with explicit hand-calcs. The bolt
coefficients are now transcribed + verified against the official SANS 10162-1:2011 PDF
(cl. 13.1/13.10/13.12), 2026-06-15; the end-plate *method* (flange-force couple, simplified
T-stub) and final registered-engineer sign-off are still required. These tests guard the
implementation.

Run:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_connections.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.connections.bolts import (
    BoltSpec,
    bolt_bearing_resistance_kn,
    bolt_shear_resistance_kn,
    bolt_tension_resistance_kn,
    make_bolt,
)
from torenone_kernel.connections.moment_endplate import (
    EndPlateConnection,
    check_moment_connection,
    design_moment_connection,
)
from torenone_kernel.models.enums import SteelGrade
from torenone_kernel.models.results import ConnectionDesignResult

# ---------------------------------------------------------------------------
# 1. Bolt resistances — pinned hand-calcs (SANS 10162-1 cl. 13.12)
# ---------------------------------------------------------------------------


class TestBoltResistances:
    def test_m20_88_tension(self):
        # SANS cl. 13.12.1.3: Tr = 0.75·φb·Ab·fu, Ab=π/4·20²=314.16, fu=830 (cl. 13.12.1.2 NOTE)
        # = 0.75·0.80·314.16·830 = 156 451 N = 156.45 kN
        assert bolt_tension_resistance_kn(make_bolt("M20", "8.8")) == pytest.approx(156.45, rel=1e-3)

    def test_m20_88_shear(self):
        # SANS cl. 13.12.1.2: Vr = 0.60·φb·Ab·fu × 0.70 (threads in shear plane)
        # = 0.70·0.60·0.80·314.16·830 = 87 613 N = 87.61 kN
        assert bolt_shear_resistance_kn(make_bolt("M20", "8.8")) == pytest.approx(87.61, rel=1e-3)

    def test_m20_bearing_on_20mm_plate(self):
        # SANS cl. 13.10(c): Br = 3·φbr·t·d·fu, φbr=0.67 = 3·0.67·20·20·470 = 377 880 N = 377.88 kN
        br = bolt_bearing_resistance_kn(make_bolt("M20", "8.8"), 20.0, 470.0)
        assert br == pytest.approx(377.88, rel=1e-3)

    def test_grade_1090_is_stronger(self):
        t88 = bolt_tension_resistance_kn(make_bolt("M24", "8.8"))
        t109 = bolt_tension_resistance_kn(make_bolt("M24", "10.9"))
        assert t109 > t88
        # M24 10.9: 0.75·0.80·(π/4·24²=452.39)·1040 = 282 291 N = 282.29 kN
        assert t109 == pytest.approx(282.29, rel=1e-3)

    def test_unknown_size_or_grade_raises(self):
        with pytest.raises(ValueError):
            make_bolt("M12", "8.8")
        with pytest.raises(ValueError):
            make_bolt("M20", "12.9")

    def test_two_shear_planes_doubles_shear(self):
        bolt = make_bolt("M20", "8.8")
        one = bolt_shear_resistance_kn(bolt, shear_planes=1)
        two = bolt_shear_resistance_kn(bolt, shear_planes=2)
        assert two == pytest.approx(2.0 * one)


# ---------------------------------------------------------------------------
# 2. check_moment_connection — demand/capacity logic
# ---------------------------------------------------------------------------


def _conn(bolt: BoltSpec | None = None, plate_t: float = 20.0, weld_leg: float = 8.0) -> EndPlateConnection:
    return EndPlateConnection(
        bolt=bolt or make_bolt("M20", "8.8"),
        n_tension_bolts=4,
        n_total_bolts=6,
        lever_arm_mm=500.0,
        plate_thickness_mm=plate_t,
        plate_fy_mpa=345.0,
        plate_fu_mpa=470.0,
        plate_trib_width_mm=80.0,
        bolt_to_weld_mm=45.0,
        weld_leg_mm=weld_leg,
        weld_length_mm=320.0,
    )


class TestCheckMomentConnection:
    def test_returns_six_checks(self):
        checks = check_moment_connection(_conn(), 86.0, 30.0, -40.0)
        assert len(checks) == 6
        names = {c.name for c in checks}
        assert "connection: bolt tension" in names
        assert "connection: flange weld" in names

    def test_tension_utilisation_matches_handcalc(self):
        # M=86 kN·m, z=500 mm -> T_flange = 86·1000/500 = 172 kN; /4 tension bolts = 43 kN/bolt
        # Tr(M20 8.8) = 156.45 kN -> util = 43/156.45 = 0.2749
        checks = check_moment_connection(_conn(), 86.0, 0.0, 0.0)
        tension = next(c for c in checks if c.name == "connection: bolt tension")
        assert tension.utilisation == pytest.approx(43.0 / 156.45, rel=1e-3)
        assert tension.passed

    def test_shear_utilisation_matches_handcalc(self):
        # V=60 kN / 6 bolts = 10 kN/bolt; Vr=87.61 -> util = 0.1142
        checks = check_moment_connection(_conn(), 0.0, 60.0, 0.0)
        shear = next(c for c in checks if c.name == "connection: bolt shear")
        assert shear.utilisation == pytest.approx(10.0 / 87.61, rel=1e-3)

    def test_combined_is_linear(self):
        # SANS cl. 13.12.1.4 bearing-type: Vu/Vr + Tu/Tr ≤ 1.4 (reported normalised by 1.4).
        checks = check_moment_connection(_conn(), 86.0, 60.0, 0.0)
        by = {c.name: c.utilisation for c in checks}
        ut = by["connection: bolt tension"]
        us = by["connection: bolt shear"]
        uc = by["connection: bolt tension+shear interaction"]
        assert uc == pytest.approx((ut + us) / 1.4, rel=1e-3)

    def test_tensile_axial_increases_bolt_tension(self):
        no_axial = check_moment_connection(_conn(), 86.0, 0.0, 0.0)
        with_axial = check_moment_connection(_conn(), 86.0, 0.0, 120.0)
        u0 = next(c.utilisation for c in no_axial if c.name == "connection: bolt tension")
        u1 = next(c.utilisation for c in with_axial if c.name == "connection: bolt tension")
        assert u1 > u0

    def test_compressive_axial_does_not_increase_tension(self):
        base = check_moment_connection(_conn(), 86.0, 0.0, 0.0)
        comp = check_moment_connection(_conn(), 86.0, 0.0, -150.0)
        u0 = next(c.utilisation for c in base if c.name == "connection: bolt tension")
        u1 = next(c.utilisation for c in comp if c.name == "connection: bolt tension")
        assert u1 == pytest.approx(u0)

    def test_huge_moment_fails_tension(self):
        checks = check_moment_connection(_conn(), 2000.0, 0.0, 0.0)
        tension = next(c for c in checks if c.name == "connection: bolt tension")
        assert not tension.passed
        assert tension.utilisation > 1.0

    def test_every_check_cites_sans_and_is_provisional(self):
        for c in check_moment_connection(_conn(), 86.0, 30.0, 0.0):
            assert "SANS 10162-1" in c.clause
            assert "PROVISIONAL" in c.clause


# ---------------------------------------------------------------------------
# 3. design_moment_connection — auto-selection
# ---------------------------------------------------------------------------

# Representative rafter (≈ 305×165×54): depth, flange width, flange thickness (mm).
_RAFTER = dict(member_depth_mm=310.0, member_flange_width_mm=166.0, member_flange_thickness_mm=13.7)


class TestDesignConnection:
    def test_eaves_passes_for_standard_frame(self):
        r = design_moment_connection(
            location="eaves", moment_knm=86.0, shear_kn=45.0, axial_kn=-40.0,
            steel_grade=SteelGrade.S355JR, **_RAFTER,
        )
        assert isinstance(r, ConnectionDesignResult)
        assert r.location == "eaves"
        assert r.passed
        assert r.max_utilisation <= 1.0
        assert "grade" in r.description

    def test_apex_label(self):
        r = design_moment_connection(
            location="apex", moment_knm=67.0, shear_kn=20.0, axial_kn=-30.0,
            steel_grade=SteelGrade.S355JR, **_RAFTER,
        )
        assert r.location == "apex"
        assert r.passed

    def test_larger_moment_escalates_or_fails(self):
        small = design_moment_connection(
            location="eaves", moment_knm=80.0, shear_kn=40.0, axial_kn=0.0,
            steel_grade=SteelGrade.S355JR, **_RAFTER,
        )
        big = design_moment_connection(
            location="eaves", moment_knm=600.0, shear_kn=200.0, axial_kn=0.0,
            steel_grade=SteelGrade.S355JR, **_RAFTER,
        )
        # The bigger demand must need a heavier connection (or fail outright).
        assert big.description != small.description or not big.passed

    def test_unsatisfiable_returns_failing_strongest(self):
        r = design_moment_connection(
            location="eaves", moment_knm=100_000.0, shear_kn=5_000.0, axial_kn=0.0,
            steel_grade=SteelGrade.S355JR, **_RAFTER,
        )
        assert not r.passed
        assert "M30" in r.description   # strongest bolt tried

    def test_deterministic(self):
        kwargs = dict(
            location="eaves", moment_knm=86.0, shear_kn=45.0, axial_kn=-40.0,
            steel_grade=SteelGrade.S355JR, **_RAFTER,
        )
        a = design_moment_connection(**kwargs)
        b = design_moment_connection(**kwargs)
        assert a.model_dump(mode="json") == b.model_dump(mode="json")

    def test_result_aggregates_pass_and_utilisation(self):
        r = design_moment_connection(
            location="eaves", moment_knm=86.0, shear_kn=45.0, axial_kn=-40.0,
            steel_grade=SteelGrade.S355JR, **_RAFTER,
        )
        assert r.passed == all(c.passed for c in r.checks)
        assert r.max_utilisation == pytest.approx(max(c.utilisation for c in r.checks))
