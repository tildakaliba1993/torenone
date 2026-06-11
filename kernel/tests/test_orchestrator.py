"""Task 1.12 — end-to-end orchestrator tests.

design(spec) → DesignResult must:
    - Choose rafter + column sections from the SAISC library
    - Run all SANS 10162-1 strength checks (classification, axial, shear, moment/LTB,
      beam-column interaction, vertical deflection SLS, sway sensitivity)
    - Return a DesignResult with every CheckResult citing a SANS clause (PRD FR-18)
    - Embed rules_version (PRD FR-20)
    - Be deterministic: same spec + version → identical result (Task 1.13 builds on this)

Fixture: a typical South African single-bay industrial portal frame.
    span=15 m, eaves=5 m, pitch=8°, bay spacing=6 m, 5 bays
    Dead roof=0.20 kPa; wind vb=36 m/s, terrain B; S355JR; pinned base.
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
from torenone_kernel.models.results import CheckResult, DesignResult, SectionChoice
from torenone_kernel.sections.library import SectionLibrary

# ---------------------------------------------------------------------------
# Standard test fixture
# ---------------------------------------------------------------------------

def _standard_spec() -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0,
            eaves_height_m=5.0,
            roof_pitch_deg=8.0,
            bay_spacing_m=6.0,
            number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(
            basic_wind_speed_ms=36.0,
            terrain_category=TerrainCategory.B,
            site_altitude_m=0.0,
            has_dominant_opening=False,
        ),
    )


# ---------------------------------------------------------------------------
# Contract tests — DesignResult shape
# ---------------------------------------------------------------------------

class TestDesignContract:
    def test_returns_design_result(self):
        r = design(_standard_spec())
        assert isinstance(r, DesignResult)

    def test_sections_has_rafter_and_column(self):
        r = design(_standard_spec())
        members = {s.member for s in r.sections}
        assert "rafter" in members
        assert "column" in members

    def test_sections_are_section_choice_instances(self):
        r = design(_standard_spec())
        assert all(isinstance(s, SectionChoice) for s in r.sections)

    def test_chosen_sections_are_in_library(self):
        lib = SectionLibrary.load_default()
        r = design(_standard_spec())
        for s in r.sections:
            assert s.designation in lib, (
                f"Section {s.designation!r} (member={s.member}) not found in library"
            )

    def test_checks_are_check_result_instances(self):
        r = design(_standard_spec())
        assert r.checks
        assert all(isinstance(c, CheckResult) for c in r.checks)

    def test_all_checks_have_clause_refs(self):
        """PRD FR-18: every check must carry a SANS clause reference."""
        r = design(_standard_spec())
        bad = [c.name for c in r.checks if not c.clause]
        assert bad == [], f"Checks missing clause ref: {bad}"

    def test_rules_version_populated(self):
        """PRD FR-20: audit trail — every result carries the pinned standard editions."""
        r = design(_standard_spec())
        assert r.rules_version
        assert "SANS 10162-1" in r.rules_version


# ---------------------------------------------------------------------------
# Correctness tests
# ---------------------------------------------------------------------------

class TestDesignCorrectness:
    def test_result_passed(self):
        """A standard reasonable frame must yield a passing DesignResult."""
        r = design(_standard_spec())
        failing = [c for c in r.checks if not c.passed]
        assert r.passed, (
            "DesignResult failed. Failing checks:\n"
            + "\n".join(f"  {c.name}: util={c.utilisation:.3f}" for c in failing)
        )

    def test_governing_utilisation_le_one(self):
        r = design(_standard_spec())
        assert r.governing_utilisation <= 1.0, (
            f"Governing utilisation {r.governing_utilisation:.3f} > 1.0"
        )

    def test_governing_utilisation_consistent(self):
        r = design(_standard_spec())
        expected = max(c.utilisation for c in r.checks)
        assert r.governing_utilisation == pytest.approx(expected, rel=1e-9)

    def test_each_section_designation_non_empty(self):
        r = design(_standard_spec())
        for s in r.sections:
            assert s.designation.strip(), f"Empty designation for member {s.member!r}"


# ---------------------------------------------------------------------------
# Determinism test (core of Task 1.13)
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_two_calls_identical_result(self):
        """Same spec → identical DesignResult (model_dump covers all fields)."""
        spec = _standard_spec()
        r1 = design(spec)
        r2 = design(spec)
        assert r1.model_dump() == r2.model_dump(), (
            "design() produced different results on two calls with the same spec"
        )

    def test_different_spec_different_result(self):
        """Changing the bay spacing changes tributary loads and must change the result."""
        spec_a = _standard_spec()
        # Narrower bay spacing → lower tributary loads → lighter sections expected
        spec_b = FrameSpec(
            geometry=FrameGeometry(
                span_m=spec_a.geometry.span_m,
                eaves_height_m=spec_a.geometry.eaves_height_m,
                roof_pitch_deg=spec_a.geometry.roof_pitch_deg,
                bay_spacing_m=3.0,   # half the standard spacing → half the UDLs
                number_of_bays=spec_a.geometry.number_of_bays,
            ),
            dead=spec_a.dead,
            wind=WindContext(
                basic_wind_speed_ms=spec_a.wind.basic_wind_speed_ms,
                terrain_category=spec_a.wind.terrain_category,
                site_altitude_m=spec_a.wind.site_altitude_m,
                has_dominant_opening=spec_a.wind.has_dominant_opening,
            ),
        )
        r_a = design(spec_a)
        r_b = design(spec_b)
        assert r_a.model_dump() != r_b.model_dump(), (
            "design() returned identical results for different specs"
        )
