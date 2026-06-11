"""Task 1.9 — second-order sway check tests.

SANS 10162-1:2011 cl. 8.7: elastic second-order effects accounted for by amplifying
translational load effects by the factor U2 = 1/(1 - ΣΔu·Cu/(ΣVu·h)).

Notional horizontal force = 0.005 × total factored gravity load (same clause).
Sway-sensitivity threshold: U2 > 1.4 (CSA S16 basis — PROVISIONAL pending SANS engineer
sign-off; SANS 10162-1 cl. 8.7 does not state an explicit numerical cutoff in the text
examined).

All drift values fed into the formula tests below are exact (derived analytically or from
verified PyNite numbers), so rel tolerances of ≤ 1% are appropriate.
"""

from __future__ import annotations

import math

import pytest
from torenone_kernel.analysis.sway_check import (
    FrameUnstableError,
    compute_sway_check,
    u2_factor,
)
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import SwaySensitivityResult
from torenone_kernel.sections.properties import SectionProperties

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(Iz_mm4=20e6, A_mm2=6000.0, Iy_mm4=1e6) -> SectionProperties:
    return SectionProperties(
        designation="TEST",
        mass_per_metre_kg_m=15.0,
        area_mm2=A_mm2,
        depth_mm=200.0,
        width_mm=100.0,
        web_thickness_mm=5.6,
        flange_thickness_mm=8.5,
        second_moment_ix_mm4=Iz_mm4,
        second_moment_iy_mm4=Iy_mm4,
        elastic_modulus_sx_mm3=Iz_mm4 / 100.0,
        plastic_modulus_zx_mm3=Iz_mm4 / 90.0,
        radius_gyration_rx_mm=math.sqrt(Iz_mm4 / A_mm2),
        radius_gyration_ry_mm=math.sqrt(Iy_mm4 / A_mm2),
        torsion_constant_j_mm4=1e4,
        warping_constant_cw_mm6=1e10,
    )


def _spec(
    span_m=20.0,
    eaves_height_m=6.0,
    roof_pitch_deg=10.0,
    bay_spacing_m=6.0,
) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=span_m,
            eaves_height_m=eaves_height_m,
            roof_pitch_deg=roof_pitch_deg,
            bay_spacing_m=bay_spacing_m,
            number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.3),
        wind=WindContext(
            basic_wind_speed_ms=28.0,
            terrain_category=TerrainCategory.B,
        ),
    )


# ---------------------------------------------------------------------------
# Unit tests for the pure u2_factor() formula
# ---------------------------------------------------------------------------

class TestU2FormulaExact:
    """Verify the U2 arithmetic directly — no PyNite involved."""

    def test_zero_drift_gives_one(self):
        # θ = 0 → rigid frame → U2 = 1.0
        assert u2_factor(drift_mm=0.0, total_vertical_kn=100.0,
                         notional_force_kn=0.5, height_mm=6000.0) == pytest.approx(1.0)

    def test_known_theta(self):
        # θ = Δ·P/(H·h) = 1.0×200/(1.0×1000) = 0.2 → U2 = 1/(1-0.2) = 1.25
        assert u2_factor(drift_mm=1.0, total_vertical_kn=200.0,
                         notional_force_kn=1.0, height_mm=1000.0) == pytest.approx(1.25, rel=1e-6)

    def test_theta_half_gives_two(self):
        # θ = 0.5 → U2 = 2.0
        assert u2_factor(drift_mm=5.0, total_vertical_kn=200.0,
                         notional_force_kn=1.0, height_mm=2000.0) == pytest.approx(2.0, rel=1e-6)

    def test_sensitivity_flag_below_threshold(self):
        # U2 = 1.25 < 1.4 → not sway-sensitive
        u2 = u2_factor(drift_mm=1.0, total_vertical_kn=200.0,
                       notional_force_kn=1.0, height_mm=1000.0)
        assert u2 < 1.4

    def test_sensitivity_flag_above_threshold(self):
        # θ = 0.5 → U2 = 2.0 > 1.4
        u2 = u2_factor(drift_mm=5.0, total_vertical_kn=200.0,
                       notional_force_kn=1.0, height_mm=2000.0)
        assert u2 > 1.4

    def test_theta_gte_one_raises(self):
        # θ = 2.0 ≥ 1.0 → FrameUnstableError
        with pytest.raises(FrameUnstableError):
            u2_factor(drift_mm=20.0, total_vertical_kn=200.0,
                      notional_force_kn=1.0, height_mm=2000.0)


# ---------------------------------------------------------------------------
# U2 validated against exact drift formula (cantilever column analogy)
# ---------------------------------------------------------------------------

class TestU2ExactCantileverDerivation:
    """Derive the expected U2 from the exact cantilever drift formula and compare.

    For a fixed-base column (height h, EI), axial load P, horizontal force H:
        Δ = H·h³/(3EI)
        θ = Δ·P/(H·h) = P·h²/(3EI)
        U2 = 1/(1 - P·h²/(3EI))

    This checks that the formula in u2_factor() matches the derivation exactly.
    """
    E = 200_000.0   # MPa
    I = 20e6        # mm⁴  # noqa: E741 — I is the standard symbol for second moment of area
    h = 5_000.0     # mm
    P_kn = 100.0    # kN  (factored gravity)
    H_kn = 0.5      # kN  (notional = 0.005 × P)

    def test_u2_matches_exact_derivation(self):
        P_N = self.P_kn * 1_000
        H_N = self.H_kn * 1_000
        # exact drift from cantilever formula (mm)
        delta = H_N * self.h**3 / (3 * self.E * self.I)
        # exact θ (N/mm units throughout)
        theta_direct = P_N * self.h**2 / (3 * self.E * self.I)
        u2_expected = 1.0 / (1.0 - theta_direct)

        u2_computed = u2_factor(
            drift_mm=delta,
            total_vertical_kn=self.P_kn,
            notional_force_kn=self.H_kn,
            height_mm=self.h,
        )
        assert u2_computed == pytest.approx(u2_expected, rel=1e-6)


# ---------------------------------------------------------------------------
# compute_sway_check() integration tests
# ---------------------------------------------------------------------------

class TestComputeSwayCheck:
    """Integration: compute_sway_check() builds a portal, runs analysis, returns result."""

    def _run(self, Iz_mm4=200e6, gravity_kn=100.0) -> SwaySensitivityResult:
        spec = _spec()
        sec = _section(Iz_mm4=Iz_mm4)
        return compute_sway_check(
            spec=spec,
            column_section=sec,
            rafter_section=sec,
            total_factored_gravity_kn=gravity_kn,
            combination_name="ULS1",
        )

    def test_returns_sway_sensitivity_result(self):
        assert isinstance(self._run(), SwaySensitivityResult)

    def test_combination_name_preserved(self):
        r = self._run()
        assert r.combination == "ULS1"

    def test_notional_force_equals_0005_gravity(self):
        r = self._run(gravity_kn=100.0)
        assert r.notional_force_kn == pytest.approx(0.5, rel=1e-6)  # 0.005 × 100

    def test_u2_at_least_one(self):
        """U2 must be ≥ 1.0 for any positive gravity load."""
        r = self._run()
        assert r.U2 >= 1.0

    def test_stiff_portal_not_sway_sensitive(self):
        """Very stiff section (large Iz) → small drift → U2 close to 1, not sway-sensitive."""
        r = self._run(Iz_mm4=500e6, gravity_kn=50.0)
        assert not r.is_sway_sensitive
        assert r.U2 < 1.4

    def test_slender_portal_sway_sensitive(self):
        """Small section (Iz=5e6 mm⁴) + modest gravity (50 kN) → U2 ≈ 5.6 → sway-sensitive.
        (Verified: Iz=5e6, G=50kN gives θ≈0.82, U2≈5.6 via PyNite.)
        """
        r = self._run(Iz_mm4=5e6, gravity_kn=50.0)
        assert r.is_sway_sensitive
        assert r.U2 > 1.4

    def test_unstable_frame_raises(self):
        """θ ≥ 1.0 (frame collapses under P-Δ) → FrameUnstableError, not a silent wrong result."""
        with pytest.raises(FrameUnstableError):
            self._run(Iz_mm4=2e6, gravity_kn=50.0)

    def test_u2_increases_with_gravity(self):
        """Greater gravity load → greater U2 (more sway)."""
        r_light = self._run(Iz_mm4=50e6, gravity_kn=10.0)
        r_heavy = self._run(Iz_mm4=50e6, gravity_kn=200.0)
        assert r_heavy.U2 > r_light.U2

    def test_eaves_drift_positive(self):
        """Lateral drift under a horizontal force must be positive (force is in +X)."""
        r = self._run()
        assert r.eaves_drift_mm > 0.0

    def test_stability_index_consistent_with_u2(self):
        """θ = 1 - 1/U2 must be consistent."""
        r = self._run()
        expected_theta = 1.0 - 1.0 / r.U2
        assert r.stability_index == pytest.approx(expected_theta, rel=1e-6)
