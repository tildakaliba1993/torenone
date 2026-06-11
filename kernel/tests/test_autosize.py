"""Task 1.11 — auto-sizing tests.

The auto-sizer iterates a SectionLibrary lightest-first and returns the first section
whose SANS 10162-1:2011 checks all pass (classification, axial Cr, shear Vr, moment Mr
with LTB, beam-column interaction, deflection is a separate SLS check not included in
the strength loop).

Strategy: build a deterministic mini-library of 3 synthetic sections (TINY < MEDIUM < LARGE
in mass order), apply loads that cause TINY to fail and MEDIUM to pass. Verify MEDIUM is
returned. Also test with the real 64-section SAISC library.

Hand-check: with fy=355 MPa, LTB_mm→0 (laterally supported), small Cu:
    TINY  Zpl=100 000 mm³  → Mr≈31.9 kN·m  (0.9×100000×355/1e6)
    MEDIUM Zpl=500 000 mm³  → Mr≈159.8 kN·m
    LARGE  Zpl=2 000 000 mm³ → Mr≈639 kN·m
Apply Mu=100 kN·m, Cu=50 kN, KL=5 000 mm → TINY fails (Mr<<Mu), MEDIUM passes.
"""

from __future__ import annotations

import pytest
from torenone_kernel.checks.autosize import (
    AutosizeResult,
    NoSectionFoundError,
    autosize_member,
)
from torenone_kernel.models.results import CheckResult
from torenone_kernel.sections.library import SectionLibrary
from torenone_kernel.sections.properties import SectionProperties

# ---------------------------------------------------------------------------
# Helpers — synthetic mini-library
# ---------------------------------------------------------------------------

def _make_section(
    tag: str,
    mass: float,
    Zpl_mm3: float,
    Ze_mm3: float,
    A_mm2: float,
    ry_mm: float,
    rx_mm: float,
    Iy_mm4: float,
    Ix_mm4: float,
    tf_mm: float = 10.0,
    tw_mm: float = 6.0,
    flange_width: float = 100.0,
    depth: float = 200.0,
    J_mm4: float = 1e4,
    Cw_mm6: float = 1e10,
) -> SectionProperties:
    """Build a SectionProperties with explicit key values for testing."""
    return SectionProperties(
        designation=tag,
        mass_per_metre_kg_m=mass,
        area_mm2=A_mm2,
        depth_mm=depth,
        width_mm=flange_width,
        web_thickness_mm=tw_mm,
        flange_thickness_mm=tf_mm,
        second_moment_ix_mm4=Ix_mm4,
        second_moment_iy_mm4=Iy_mm4,
        elastic_modulus_sx_mm3=Ze_mm3,
        plastic_modulus_zx_mm3=Zpl_mm3,
        radius_gyration_rx_mm=rx_mm,
        radius_gyration_ry_mm=ry_mm,
        torsion_constant_j_mm4=J_mm4,
        warping_constant_cw_mm6=Cw_mm6,
    )


def _mini_library() -> SectionLibrary:
    """Three sections ordered TINY < MEDIUM < LARGE by mass, all class-1 flanges."""
    # Flange b/t = (50/2)/10 = 2.5 << 7.7 → class 1 flange always
    # Web h/t = (200-20)/6 = 30 → class 1 web always (< 58.4 for fy=355)
    tiny = _make_section(
        "TINY", mass=5.0,
        Zpl_mm3=100_000, Ze_mm3=87_000,
        A_mm2=1500, ry_mm=15, rx_mm=80,
        Iy_mm4=337_500, Ix_mm4=9_600_000,
    )
    medium = _make_section(
        "MEDIUM", mass=25.0,
        Zpl_mm3=500_000, Ze_mm3=435_000,
        A_mm2=5000, ry_mm=30, rx_mm=100,
        Iy_mm4=4_500_000, Ix_mm4=50_000_000,
    )
    large = _make_section(
        "LARGE", mass=80.0,
        Zpl_mm3=2_000_000, Ze_mm3=1_740_000,
        A_mm2=15_000, ry_mm=60, rx_mm=200,
        Iy_mm4=54_000_000, Ix_mm4=600_000_000,
    )
    return SectionLibrary([tiny, medium, large])


# Loads: Mu=100 kN·m, Cu=50 kN (small), Vu=30 kN
# KL=5000 mm, LTB_mm=1 mm (effectively laterally supported)
_FY = 355.0
_MU = 100.0   # kN·m  — TINY fails (Mr≈31.9), MEDIUM passes (Mr≈159.8)
_CU = 50.0    # kN
_VU = 30.0    # kN
_KL = 5_000.0
_LTB = 1.0    # mm — effectively fully restrained → Mcr huge → Mr = φ·Mp


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------

class TestAutosizeMiniLibrary:
    def _run(self, mu=_MU, cu=_CU, vu=_VU):
        return autosize_member(
            library=_mini_library(),
            fy_mpa=_FY,
            cu_kn=cu,
            vu_kn=vu,
            mu_knm=mu,
            KL_mm=_KL,
            LTB_mm=_LTB,
            omega2=1.0,
            U1=1.0,
        )

    def test_returns_autosize_result(self):
        assert isinstance(self._run(), AutosizeResult)

    def test_skips_tiny_chooses_medium(self):
        """Mu=100 kN·m → TINY (Mr≈31.9) fails, MEDIUM (Mr≈159.8) passes."""
        r = self._run()
        assert r.section.designation == "MEDIUM"

    def test_result_is_passing(self):
        r = self._run()
        assert r.passed

    def test_checks_are_check_results(self):
        r = self._run()
        assert all(isinstance(c, CheckResult) for c in r.checks)
        assert len(r.checks) > 0

    def test_all_checks_pass(self):
        r = self._run()
        failing = [c for c in r.checks if not c.passed]
        assert failing == [], f"Failing checks on chosen section: {[c.name for c in failing]}"

    def test_max_utilisation_le_one(self):
        r = self._run()
        assert r.max_utilisation <= 1.0

    def test_max_utilisation_consistent(self):
        r = self._run()
        assert r.max_utilisation == pytest.approx(max(c.utilisation for c in r.checks), rel=1e-6)

    def test_section_class_is_int_123(self):
        r = self._run()
        assert r.section_class_value in (1, 2, 3)

    def test_no_section_found_raises(self):
        """Absurdly large Mu → no section can satisfy → NoSectionFoundError."""
        with pytest.raises(NoSectionFoundError):
            autosize_member(
                library=_mini_library(),
                fy_mpa=_FY,
                cu_kn=0.0,
                vu_kn=0.0,
                mu_knm=100_000.0,   # 100 MN·m — impossible for any section
                KL_mm=_KL,
                LTB_mm=_LTB,
                omega2=1.0,
                U1=1.0,
            )

    def test_light_load_picks_tiny(self):
        """Very small Mu → TINY should suffice.

        Use KL=1000 mm so TINY's slenderness (ry=15 → KL/r=67) stays under 200 (cl. 10.4.2.1).
        With KL=5000, TINY (ry=15 → KL/r=333) would be skipped as overly slender — that is
        correct code behaviour, so this test deliberately uses a short effective length.
        """
        r = autosize_member(
            library=_mini_library(),
            fy_mpa=_FY,
            cu_kn=0.0,
            vu_kn=1.0,
            mu_knm=5.0,   # well below TINY Mr ≈ 31.9 kN·m
            KL_mm=1_000.0,  # KL/r = 1000/15 = 67 < 200 → slenderness OK
            LTB_mm=_LTB,
            omega2=1.0,
            U1=1.0,
        )
        assert r.section.designation == "TINY"

    def test_very_heavy_axial_triggers_next_section(self):
        """High Cu makes interaction ratio > 1 for TINY even with small Mu → skip to MEDIUM."""
        r = autosize_member(
            library=_mini_library(),
            fy_mpa=_FY,
            cu_kn=400.0,    # very high → TINY Cr ≈ 150 kN << 400 → fails
            vu_kn=1.0,
            mu_knm=5.0,
            KL_mm=_KL,
            LTB_mm=_LTB,
            omega2=1.0,
            U1=1.0,
        )
        assert r.section.designation in ("MEDIUM", "LARGE")

    def test_each_check_has_clause(self):
        """Every CheckResult must carry a non-empty SANS clause reference (PRD FR-18)."""
        r = self._run()
        for c in r.checks:
            assert len(c.clause) > 0, f"Check '{c.name}' has empty clause reference"


# ---------------------------------------------------------------------------
# Integration with the real SAISC library
# ---------------------------------------------------------------------------

class TestAutosizeRealLibrary:
    """Smoke tests against the real 64-section SAISC dataset.

    Loads chosen to be in a realistic range for a modest portal frame:
        Mu ≈ 80 kN·m (a common rafter moment for a 15m span, 6m bay)
        Cu ≈ 40 kN   (axial in rafter from frame action)
        Vu ≈ 25 kN   (shear)
        KL = 3 000 mm (effective length for rafter buckling check)
        LTB = 1 500 mm (purlin spacing)
    A section from the IPE/UB family should satisfy these loads.
    """

    def _run_real(self, mu=80.0, cu=40.0, vu=25.0, KL=3000.0, LTB=1500.0):
        lib = SectionLibrary.load_default()
        return autosize_member(
            library=lib,
            fy_mpa=355.0,
            cu_kn=cu,
            vu_kn=vu,
            mu_knm=mu,
            KL_mm=KL,
            LTB_mm=LTB,
            omega2=1.0,
            U1=1.0,
        )

    def test_finds_a_section(self):
        r = self._run_real()
        assert isinstance(r, AutosizeResult)
        assert r.passed

    def test_chosen_section_is_in_library(self):
        lib = SectionLibrary.load_default()
        r = self._run_real()
        assert r.section.designation in lib

    def test_chosen_section_checks_all_pass(self):
        r = self._run_real()
        assert all(c.passed for c in r.checks)

    def test_chosen_is_lightest_possible(self):
        """The chosen section must be lighter than the next heavier passing candidate.

        Verify by checking that the immediately-lighter sections in the library all fail.
        """
        lib = SectionLibrary.load_default()
        r = self._run_real()
        ordered = lib.by_increasing_mass()
        chosen_idx = next(i for i, s in enumerate(ordered)
                          if s.designation == r.section.designation)
        # All lighter sections should fail at least one check
        lighter_passed_any = False
        for sec in ordered[:chosen_idx]:
            try:
                candidate = autosize_member(
                    library=SectionLibrary([sec]),
                    fy_mpa=355.0, cu_kn=40.0, vu_kn=25.0, mu_knm=80.0,
                    KL_mm=3000.0, LTB_mm=1500.0, omega2=1.0, U1=1.0,
                )
                if candidate.passed:
                    lighter_passed_any = True
            except NoSectionFoundError:
                pass
        assert not lighter_passed_any, (
            "A lighter section also passed — autosize did not return the true lightest"
        )
