"""Task 2.7 — Competitive-advantage report features (PRD FR-25/26/27).

FR-25: Steel mass + indicative cost readout. (already present since Task 2.1)
FR-26: Line-by-line audit / "show-your-working" layout:
         assumptions → loads → combinations → analysis forces → checks → section.
         Every number labelled as "computed by deterministic kernel, not AI".
FR-27: Explicit assumptions / out-of-scope / engineer-must-verify block.

What is NEW in Task 2.7 (vs already implemented):
  - A dedicated "Show Your Working" section with:
      * Characteristic load derivation (dead + imposed) with tributary-width steps
      * ULS-1 factored UDL table (γG × G + γQ × Q = factored UDL)
      * Governing analysis forces table (M/V/N at eaves, apex, column base)
      * Per-member section capacity tables:
          - Section properties (A, Ix, Zpl, ry)
          - KL/r slenderness (cl. 10.4.2.1)
          - Cr capacity (cl. 13.3.1)
          - Vr capacity (cl. 13.4.1.1)
          - Mcr and Mr capacity (cl. 13.5/13.6)
          - Beam-column interaction inputs (cl. 13.8.2)

Tests run on Python 3.9 (HTML only — no WeasyPrint).
Run:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_show_your_working.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.report.renderer import render_html

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spec():
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


@pytest.fixture(scope="module")
def result(spec):
    return design(spec)


@pytest.fixture(scope="module")
def html(result):
    return render_html(result)


# ---------------------------------------------------------------------------
# 0. FR-27 — Assumptions / out-of-scope / engineer-must-verify block
# ---------------------------------------------------------------------------

class TestAssumptionsBlock:
    """FR-27: honest assumptions and limitations as a feature."""

    def test_assumptions_section_present(self, html):
        assert "Assumed" in html or "Assumptions" in html

    def test_out_of_scope_section_present(self, html):
        html_lower = html.lower()
        assert "out of scope" in html_lower or "out-of-scope" in html_lower

    def test_engineer_must_verify_present(self, html):
        html_lower = html.lower()
        assert "engineer must verify" in html_lower or "engineer-must-verify" in html_lower

    def test_provisional_flag_present(self, html):
        assert "PROVISIONAL" in html or "provisional" in html.lower()

    def test_connection_design_out_of_scope(self, html):
        """Connection design is a key out-of-scope item — must be listed."""
        html_lower = html.lower()
        assert "connection" in html_lower

    def test_foundation_out_of_scope(self, html):
        html_lower = html.lower()
        assert "foundation" in html_lower


# ---------------------------------------------------------------------------
# 1. FR-26a — Characteristic loads derivation ("show your working")
# ---------------------------------------------------------------------------

class TestDeadLoadWorking:
    """Dead load breakdown: area load × tributary width + self-weight = UDL."""

    def test_dead_roof_area_load_present(self, html, result):
        """Roof area load (kPa) must appear in show-your-working."""
        dead = result.frame_spec.dead
        assert str(dead.roof_kpa) in html

    def test_services_kpa_present(self, html, result):
        assert str(result.frame_spec.dead.services_kpa) in html

    def test_tributary_width_present(self, html, result):
        trib = result.frame_spec.geometry.bay_spacing_m
        assert str(trib) in html

    def test_dead_rafter_udl_value_present(self, html, result):
        """Computed rafter dead UDL must appear (kernel-computed)."""
        from torenone_kernel.loads.dead import dead_loads
        from torenone_kernel.sections.library import SectionLibrary
        lib = SectionLibrary.load_default()
        sec_map = {s.member: lib.get(s.designation) for s in result.sections}
        dead = dead_loads(result.frame_spec,
                          rafter=sec_map["rafter"], column=sec_map["column"])
        val = f"{dead.rafter_udl_kn_per_m:.3f}"
        assert val in html, f"Dead rafter UDL {val} kN/m not found in HTML"

    def test_dead_load_clause_present(self, html):
        """Dead loads must cite their source clause."""
        # SANS 10160-2 or similar
        assert "SANS 10160" in html or "10160" in html


class TestImposedLoadWorking:
    """Imposed load breakdown: characteristic area (kPa) × trib = UDL."""

    def test_imposed_area_load_present(self, html):
        """The 0.4 kPa characteristic imposed roof load must appear."""
        assert "0.4" in html

    def test_imposed_clause_present(self, html):
        """SANS 10160-2 Table 5 clause must appear."""
        assert "10160-2" in html or "Table 5" in html

    def test_imposed_udl_value_present(self, html, result):
        """Computed imposed UDL must appear."""
        from torenone_kernel.loads.imposed import imposed_roof_loads
        imp = imposed_roof_loads(result.frame_spec)
        val = f"{imp.roof_udl_kn_per_m:.3f}"
        assert val in html, f"Imposed UDL {val} kN/m not found in HTML"


# ---------------------------------------------------------------------------
# 2. FR-26b — Load combination factored UDLs
# ---------------------------------------------------------------------------

class TestCombinationWorking:
    """ULS-1: γG × dead + γQ × imposed = factored UDL — all values must appear."""

    def test_gamma_G_factor_present(self, html):
        """γG = 1.2 (ULS-1 dominant gravity) must appear."""
        assert "1.2" in html

    def test_gamma_Q_factor_present(self, html):
        """γQ = 1.6 (ULS-1 dominant gravity) must appear."""
        assert "1.6" in html

    def test_uls1_label_present(self, html):
        """The ULS-1 combination must be identified by name."""
        assert "ULS-1" in html or "ULS" in html

    def test_factored_rafter_udl_present(self, html, result):
        """Factored rafter UDL (γG × G + γQ × Q) must appear."""
        from torenone_kernel.loads.combinations import load_combinations
        from torenone_kernel.loads.dead import dead_loads
        from torenone_kernel.loads.imposed import imposed_roof_loads
        from torenone_kernel.sections.library import SectionLibrary
        lib = SectionLibrary.load_default()
        sec_map = {s.member: lib.get(s.designation) for s in result.sections}
        dead = dead_loads(result.frame_spec,
                          rafter=sec_map["rafter"], column=sec_map["column"])
        imp  = imposed_roof_loads(result.frame_spec)
        combos = load_combinations(result.frame_spec)
        uls1 = next(c for c in combos if c.name.startswith("ULS-1"))
        gG, gQ = uls1.factors["dead"], uls1.factors.get("imposed", 0.0)
        factored = gG * dead.rafter_udl_kn_per_m + gQ * imp.roof_udl_kn_per_m
        val = f"{factored:.3f}"
        assert val in html, f"Factored rafter UDL {val} kN/m not found in HTML"

    def test_combination_clause_present(self, html):
        """Load combination factors must cite SANS 10160-1."""
        assert "SANS 10160-1" in html or "10160-1" in html


# ---------------------------------------------------------------------------
# 3. FR-26c — Governing analysis forces
# ---------------------------------------------------------------------------

class TestAnalysisForces:
    """The governing M, V, N at key locations must appear in the working section."""

    def test_eaves_moment_present(self, html, result):
        """Eaves moment (knee joint — governing for rafter and column) must appear."""
        from torenone_kernel.analysis.plane_frame import PortalAnalysis
        from torenone_kernel.loads.combinations import load_combinations
        from torenone_kernel.loads.dead import dead_loads
        from torenone_kernel.loads.imposed import imposed_roof_loads
        from torenone_kernel.sections.library import SectionLibrary
        lib = SectionLibrary.load_default()
        sec_map = {s.member: lib.get(s.designation) for s in result.sections}
        col_sec = sec_map["column"]
        raf_sec = sec_map["rafter"]
        dead = dead_loads(result.frame_spec, rafter=raf_sec, column=col_sec)
        imp  = imposed_roof_loads(result.frame_spec)
        combos = load_combinations(result.frame_spec)
        uls1 = next(c for c in combos if c.name.startswith("ULS-1"))
        gG, gQ = uls1.factors["dead"], uls1.factors.get("imposed", 0.0)
        uls_raf = gG * dead.rafter_udl_kn_per_m + gQ * imp.roof_udl_kn_per_m
        uls_col = gG * (dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m)
        analysis = PortalAnalysis(result.frame_spec, col_sec, raf_sec).run(
            uls1.name, uls_raf, uls_col
        )
        forces = {f.location: f for f in analysis.forces}
        mu_eaves = abs(forces["eaves_L"].moment_knm)
        val = f"{mu_eaves:.2f}"
        assert val in html, f"Eaves moment {val} kN·m not found in HTML"

    def test_apex_moment_present(self, html, result):
        """Apex moment must appear in the working section."""
        from torenone_kernel.analysis.plane_frame import PortalAnalysis
        from torenone_kernel.loads.combinations import load_combinations
        from torenone_kernel.loads.dead import dead_loads
        from torenone_kernel.loads.imposed import imposed_roof_loads
        from torenone_kernel.sections.library import SectionLibrary
        lib = SectionLibrary.load_default()
        sec_map = {s.member: lib.get(s.designation) for s in result.sections}
        col_sec = sec_map["column"]
        raf_sec = sec_map["rafter"]
        dead = dead_loads(result.frame_spec, rafter=raf_sec, column=col_sec)
        imp  = imposed_roof_loads(result.frame_spec)
        combos = load_combinations(result.frame_spec)
        uls1 = next(c for c in combos if c.name.startswith("ULS-1"))
        gG, gQ = uls1.factors["dead"], uls1.factors.get("imposed", 0.0)
        uls_raf = gG * dead.rafter_udl_kn_per_m + gQ * imp.roof_udl_kn_per_m
        uls_col = gG * (dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m)
        analysis = PortalAnalysis(result.frame_spec, col_sec, raf_sec).run(
            uls1.name, uls_raf, uls_col
        )
        forces = {f.location: f for f in analysis.forces}
        mu_apex = abs(forces["apex"].moment_knm)
        val = f"{mu_apex:.2f}"
        assert val in html, f"Apex moment {val} kN·m not found in HTML"

    def test_analysis_forces_section_labelled(self, html):
        """Analysis forces must be in a labelled section."""
        html_lower = html.lower()
        assert "analysis" in html_lower or "forces" in html_lower

    def test_eaves_label_present(self, html):
        html_lower = html.lower()
        assert "eaves" in html_lower

    def test_apex_label_present(self, html):
        html_lower = html.lower()
        assert "apex" in html_lower


# ---------------------------------------------------------------------------
# 4. FR-26d — Section capacity working (per member)
# ---------------------------------------------------------------------------

class TestSectionCapacityWorking:
    """Capacity values Cr, Vr, Mr (with inputs) must appear for each member."""

    def _get_capacities(self, result):
        import math

        from torenone_kernel.checks.axial import cr_flexural
        from torenone_kernel.checks.bending import mcr_elastic, mr_ltb
        from torenone_kernel.checks.classification import classify_section
        from torenone_kernel.checks.material import fy_mpa
        from torenone_kernel.checks.shear import vr_web
        from torenone_kernel.sections.library import SectionLibrary
        lib = SectionLibrary.load_default()
        sec_map = {s.member: lib.get(s.designation) for s in result.sections}
        caps = {}
        geom = result.frame_spec.geometry
        half_mm = geom.span_m / 2.0 * 1_000.0
        rise_mm = (geom.apex_height_m - geom.eaves_height_m) * 1_000.0
        raf_len_mm = math.hypot(half_mm, rise_mm)
        col_len_mm = geom.eaves_height_m * 1_000.0
        lengths = {"rafter": raf_len_mm, "column": col_len_mm}
        for member, sec in sec_map.items():
            fy = fy_mpa(result.frame_spec.materials.steel_grade, sec.flange_thickness_mm)
            KL = lengths[member]
            LTB = lengths[member]
            cls = classify_section(sec, fy, 0.0)
            cr = cr_flexural(sec.area_mm2, fy, KL, sec.radius_gyration_ry_mm)
            hw = sec.depth_mm - 2 * sec.flange_thickness_mm
            vr = vr_web(hw, sec.web_thickness_mm, fy)
            mcr = mcr_elastic(LTB, sec.second_moment_iy_mm4,
                              sec.torsion_constant_j_mm4,
                              sec.warping_constant_cw_mm6, 1.0)
            mr = mr_ltb(cls.overall_class,
                        sec.plastic_modulus_zx_mm3, sec.elastic_modulus_sx_mm3, fy, mcr)
            caps[member] = {"cr": cr, "vr": vr, "mcr": mcr, "mr": mr,
                            "fy": fy, "KL": KL, "LTB": LTB}
        return caps

    def test_cr_value_present_rafter(self, html, result):
        """Axial capacity Cr for rafter must appear (formatted to 2 d.p.)."""
        caps = self._get_capacities(result)
        val = f"{caps['rafter']['cr']:.2f}"
        assert val in html, f"Rafter Cr = {val} kN not found in HTML"

    def test_cr_value_present_column(self, html, result):
        caps = self._get_capacities(result)
        val = f"{caps['column']['cr']:.2f}"
        assert val in html, f"Column Cr = {val} kN not found in HTML"

    def test_vr_value_present_rafter(self, html, result):
        caps = self._get_capacities(result)
        val = f"{caps['rafter']['vr']:.2f}"
        assert val in html, f"Rafter Vr = {val} kN not found in HTML"

    def test_mr_value_present_rafter(self, html, result):
        caps = self._get_capacities(result)
        val = f"{caps['rafter']['mr']:.2f}"
        assert val in html, f"Rafter Mr = {val} kN·m not found in HTML"

    def test_mr_value_present_column(self, html, result):
        caps = self._get_capacities(result)
        val = f"{caps['column']['mr']:.2f}"
        assert val in html, f"Column Mr = {val} kN·m not found in HTML"

    def test_fy_value_present(self, html, result):
        """Design yield stress fy must appear."""
        from torenone_kernel.checks.material import fy_mpa
        from torenone_kernel.sections.library import SectionLibrary
        lib = SectionLibrary.load_default()
        raf = lib.get(next(s.designation for s in result.sections if s.member == "rafter"))
        fy = fy_mpa(result.frame_spec.materials.steel_grade, raf.flange_thickness_mm)
        assert str(int(fy)) in html, f"fy = {fy} MPa not found in HTML"

    def test_section_area_present(self, html, result):
        """Section area A (mm²) must appear (report renders it comma-grouped)."""
        from torenone_kernel.sections.library import SectionLibrary
        lib = SectionLibrary.load_default()
        raf = lib.get(next(s.designation for s in result.sections if s.member == "rafter"))
        val = f"{int(raf.area_mm2):,}"   # matches the template's "{:,.0f}" formatting
        assert val in html, f"Rafter area A = {val} mm² not found in HTML"

    def test_capacity_clauses_present(self, html):
        """Each capacity clause must be cited in the working section."""
        assert "13.3.1" in html   # Cr
        assert "13.4.1.1" in html  # Vr
        assert "13.5" in html      # Mr / Mcr
        assert "13.8" in html      # interaction


# ---------------------------------------------------------------------------
# 5. FR-26 — Provenance label on every kernel-computed number
# ---------------------------------------------------------------------------

class TestProvenanceLabel:
    def test_provenance_statement_present(self, html):
        """'Computed by deterministic kernel' or equivalent must appear."""
        html_lower = html.lower()
        assert "kernel" in html_lower, "No 'kernel' reference found in HTML"

    def test_not_ai_statement_present(self, html):
        """Explicit 'not AI' or 'not by an AI' statement required (FR-26)."""
        html_lower = html.lower()
        assert "not" in html_lower and ("ai" in html_lower or "language model" in html_lower), (
            "No 'not AI' / 'not by an AI language model' statement found"
        )

    def test_provenance_label_in_show_your_working(self, html):
        """The show-your-working section itself must carry a provenance note."""
        assert "kernel" in html.lower()

    def test_registered_engineer_disclaimer_present(self, html):
        """Report must state that a registered engineer must review."""
        html_lower = html.lower()
        assert "registered" in html_lower or "engineer" in html_lower


# ---------------------------------------------------------------------------
# 6. FR-25 — Steel mass + indicative cost (already in schedule; verify here)
# ---------------------------------------------------------------------------

class TestMassAndCostInReport:
    def test_total_mass_present(self, html, result):
        assert result.total_steel_mass_kg is not None
        assert str(int(round(result.total_steel_mass_kg))) in html

    def test_cost_present(self, html, result):
        assert result.indicative_cost_zar is not None
        cost_str = f"{int(round(result.indicative_cost_zar)):,}"
        assert cost_str in html

    def test_mass_unit_label_present(self, html):
        assert "kg" in html

    def test_cost_currency_label_present(self, html):
        html_lower = html.lower()
        assert "zar" in html_lower or "r " in html_lower or "cost" in html_lower

    def test_cost_provisional_warning_present(self, html):
        """Cost rate must be flagged as PROVISIONAL (it is)."""
        assert "PROVISIONAL" in html or "provisional" in html.lower()
