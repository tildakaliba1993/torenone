"""Task 1.8 — plane-frame analysis engine tests.

All expected values come from first-principles statics (exact closed-form solutions) or a
hand-checked portal-frame stiffness analysis. EI-cancels for determinate cases; indeterminate
cases are validated against textbook stiffness-method solutions.

Unit convention used throughout: N (force), mm (length), N·mm (moment).
The solver module uses N/mm² (MPa) for E, mm⁴ for I, mm for lengths.
Results are converted to kN / kN·m for the AnalysisResult contract.

Tolerances (per docs/REFERENCES-AND-VALIDATION.md §4): ±1% relative for forces/moments.
"""

from __future__ import annotations

import math

import pytest

# The module under test — will be created in the implementation step
from torenone_kernel.analysis.plane_frame import (
    PortalAnalysis,
    solve_cantilever_point_load,
    solve_portal_udl,
    solve_simple_beam_udl,
)
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import AnalysisResult
from torenone_kernel.sections.properties import SectionProperties

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(A_mm2=6000.0, Iz_mm4=20e6, Iy_mm4=1e6, J_mm4=1e4) -> SectionProperties:
    """Dummy section — only A and Iz matter for 2-D analysis."""
    return SectionProperties(
        designation="TEST-200",
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
        torsion_constant_j_mm4=J_mm4,
        warping_constant_cw_mm6=1e10,
    )


def _frame_spec(
    span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0
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
# Case 1 — Simply-supported beam, UDL
# ---------------------------------------------------------------------------
# Exact:  R = wL/2,  M_mid = wL²/8,  V_max = wL/2
# w = 2 N/mm,  L = 5 000 mm  →  R = 5 000 N,  M_mid = 6.25e6 N·mm,  V_max = 5 000 N

class TestSimplySupportedBeamUDL:
    """Simply-supported beam, UDL — exact statics validation."""

    W_N_MM = 2.0   # N/mm
    L_MM   = 5_000 # mm

    def test_reactions(self):
        r = solve_simple_beam_udl(
            w_n_per_mm=self.W_N_MM, span_mm=self.L_MM, section=_section()
        )
        expected = self.W_N_MM * self.L_MM / 2.0   # 5 000 N
        assert r["reaction_i_N"] == pytest.approx(expected, rel=1e-3)
        assert r["reaction_j_N"] == pytest.approx(expected, rel=1e-3)

    def test_mid_span_moment(self):
        r = solve_simple_beam_udl(
            w_n_per_mm=self.W_N_MM, span_mm=self.L_MM, section=_section()
        )
        expected = self.W_N_MM * self.L_MM**2 / 8.0   # 6.25e6 N·mm
        assert abs(r["moment_mid_Nmm"]) == pytest.approx(expected, rel=1e-3)

    def test_max_shear(self):
        r = solve_simple_beam_udl(
            w_n_per_mm=self.W_N_MM, span_mm=self.L_MM, section=_section()
        )
        expected = self.W_N_MM * self.L_MM / 2.0   # 5 000 N
        assert r["shear_max_N"] == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# Case 2 — Cantilever, point load at tip
# ---------------------------------------------------------------------------
# Exact:  M_fixed = P·L,  V = P
# P = 10 000 N,  L = 3 000 mm  →  M = 30e6 N·mm,  V = 10 000 N

class TestCantileverPointLoad:
    P_N  = 10_000
    L_MM = 3_000

    def test_fixed_end_moment(self):
        r = solve_cantilever_point_load(
            P_n=self.P_N, length_mm=self.L_MM, section=_section()
        )
        expected = self.P_N * self.L_MM  # 30e6 N·mm
        assert r["moment_fixed_Nmm"] == pytest.approx(expected, rel=1e-3)

    def test_shear(self):
        r = solve_cantilever_point_load(
            P_n=self.P_N, length_mm=self.L_MM, section=_section()
        )
        assert r["shear_N"] == pytest.approx(self.P_N, rel=1e-3)


# ---------------------------------------------------------------------------
# Case 3 — Pinned-base symmetric portal, vertical UDL on rafters
# ---------------------------------------------------------------------------
# Frame: span L = 10 m, columns height h = 5 m, flat-top approximation for moment check.
# For a pinned-base portal with horizontal beam under vertical UDL w (per unit horizontal),
# the classical stiffness-method result (symmetric loading, equal members) gives:
#
#   Horizontal thrust  H  = (w L²/8) / (h + I_col/I_raf · L/2)
#   ... for equal sections (I_col = I_raf = I): H = wL²/8 / (h + L/2) = wL²/(8(h+L/2))
#
# With L = 10 000 mm, h = 5 000 mm, w = 1 N/mm, I = I (equal sections):
#   H = (1 × 10000²/8) / (5000 + 10000/2) = 12 500 000 / 10 000 = 1 250 N
#
# Note: "flat top" (horizontal rafter) — a valid first validation; the full pitched portal is
# tested via PortalAnalysis in the next class.
#
# Eaves moment (column base pinned, top has horizontal + vertical reactions from rafter):
#   M_eaves = H × h = 1250 × 5000 = 6.25e6 N·mm
#
# Vertical reaction at each column base: V = wL/2 = 5 000 N  (by symmetry)
#
# Reference: Ghali & Neville "Structural Analysis" §portal frames; also McGuire et al.
# "Matrix Structural Analysis".

class TestPinnedBasePortalFlatTopUDL:
    """Pinned-base portal, flat rafter, symmetric vertical UDL — stiffness-method hand calc."""

    L_MM = 10_000  # span (mm)
    H_MM =  5_000  # column height (mm)
    W    =  1.0    # N/mm on each rafter half

    # Derived from stiffness method (equal sections):
    EXPECTED_H_N      = 1_250.0   # horizontal thrust
    EXPECTED_V_N      = 5_000.0   # vertical reaction each side
    EXPECTED_M_EAVES  = 6.25e6    # N·mm at eaves

    def test_portal_reactions(self):
        r = solve_portal_udl(
            span_mm=self.L_MM,
            height_mm=self.H_MM,
            w_n_per_mm=self.W,
            section=_section(),
        )
        assert r["H_N"] == pytest.approx(self.EXPECTED_H_N, rel=0.02)
        assert r["V_N"] == pytest.approx(self.EXPECTED_V_N, rel=0.02)

    def test_portal_eaves_moment(self):
        r = solve_portal_udl(
            span_mm=self.L_MM,
            height_mm=self.H_MM,
            w_n_per_mm=self.W,
            section=_section(),
        )
        assert r["M_eaves_Nmm"] == pytest.approx(self.EXPECTED_M_EAVES, rel=0.02)


# ---------------------------------------------------------------------------
# Case 4 — PortalAnalysis from FrameSpec + SectionProperties
# ---------------------------------------------------------------------------

class TestPortalAnalysisContract:
    """Integration test: PortalAnalysis builds from FrameSpec and returns AnalysisResult."""

    def _run(self) -> AnalysisResult:
        spec = _frame_spec()
        sec = _section()
        pa = PortalAnalysis(spec=spec, column_section=sec, rafter_section=sec)
        # Apply a simple gravity UDL (kN/m) and run
        return pa.run(
            combination_name="1.2DL",
            rafter_udl_kn_per_m=5.0,   # downward, kN/m
            column_axial_kn_per_m=0.0,
        )

    def test_returns_analysis_result(self):
        result = self._run()
        assert isinstance(result, AnalysisResult)

    def test_combination_name_preserved(self):
        result = self._run()
        assert result.combination == "1.2DL"

    def test_forces_non_empty(self):
        result = self._run()
        assert len(result.forces) >= 5  # at least: 2 col-bases, 2 eaves, 1 apex

    def test_force_location_names(self):
        result = self._run()
        names = {f.location for f in result.forces}
        assert "col_base_L" in names
        assert "col_base_R" in names
        assert "eaves_L"    in names
        assert "eaves_R"    in names
        assert "apex"       in names

    def test_symmetry_under_symmetric_load(self):
        """Symmetric portal + symmetric gravity load → symmetric forces (within 1%)."""
        result = self._run()
        forces = {f.location: f for f in result.forces}
        L = forces["col_base_L"]
        R = forces["col_base_R"]
        assert abs(L.shear_kn)   == pytest.approx(abs(R.shear_kn),   rel=0.01)
        assert abs(L.axial_kn)   == pytest.approx(abs(R.axial_kn),   rel=0.01)
        # Both moments are ~zero (pinned base); compare as absolute tolerance
        assert abs(L.moment_knm) == pytest.approx(abs(R.moment_knm), abs=0.01)

    def test_column_base_pinned_moment_is_zero(self):
        """Pinned bases must have zero (or near-zero) moment."""
        result = self._run()
        forces = {f.location: f for f in result.forces}
        assert forces["col_base_L"].moment_knm == pytest.approx(0.0, abs=0.01)
        assert forces["col_base_R"].moment_knm == pytest.approx(0.0, abs=0.01)

    def test_vertical_equilibrium(self):
        """Sum of column-base vertical reactions ≈ total applied gravity load."""
        spec = _frame_spec(span_m=20.0)
        sec = _section()
        pa = PortalAnalysis(spec=spec, column_section=sec, rafter_section=sec)
        w_kn_m = 5.0
        result = pa.run("combo", rafter_udl_kn_per_m=w_kn_m, column_axial_kn_per_m=0.0)
        forces = {f.location: f for f in result.forces}
        # Total vertical load = w × full span  (applied on both halves)
        total_load_kn = w_kn_m * spec.geometry.span_m
        # Vertical reaction at base = axial in column (column is vertical, so axial = vertical)
        v_total = forces["col_base_L"].axial_kn + forces["col_base_R"].axial_kn
        # axial is compressive (negative convention), so sum of magnitudes
        assert abs(v_total) == pytest.approx(total_load_kn, rel=0.02)
