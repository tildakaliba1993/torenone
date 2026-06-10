"""Task 1.14 — check-mode and material-readout tests.

Part A: check(spec, sections) → DesignResult
    Engineer supplies the section designations; the kernel runs all SANS 10162-1
    strength checks without auto-sizing.

Part B: total_steel_mass_kg + indicative_cost_zar on DesignResult
    Carried by both design() and check() results so engineers can read mass and
    indicative fabrication cost directly from the output (PRD FR-24/25).
"""

from __future__ import annotations

import math
import pytest

from torenone_kernel.design import check, design
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.results import CheckResult, DesignResult, SectionChoice
from torenone_kernel.sections.library import SectionLibrary


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _spec() -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


def _passing_sections() -> list[SectionChoice]:
    """Return the sections that design() picks for the standard spec — these must pass."""
    r = design(_spec())
    return list(r.sections)


def _tiny_sections() -> list[SectionChoice]:
    """Smallest sections in the library — almost certainly too small for a 15 m frame."""
    lib = SectionLibrary.load_default()
    lightest = lib.by_increasing_mass()[0]
    return [
        SectionChoice(member="rafter", designation=lightest.designation),
        SectionChoice(member="column", designation=lightest.designation),
    ]


# ---------------------------------------------------------------------------
# Part A: check() contract
# ---------------------------------------------------------------------------

class TestCheckContract:
    def test_returns_design_result(self):
        r = check(_spec(), _passing_sections())
        assert isinstance(r, DesignResult)

    def test_sections_match_input(self):
        """check() must echo back exactly the sections supplied by the engineer."""
        supplied = _passing_sections()
        r = check(_spec(), supplied)
        result_map = {s.member: s.designation for s in r.sections}
        for s in supplied:
            assert result_map[s.member] == s.designation

    def test_checks_are_check_results(self):
        r = check(_spec(), _passing_sections())
        assert r.checks
        assert all(isinstance(c, CheckResult) for c in r.checks)

    def test_all_checks_have_clause_refs(self):
        """PRD FR-18: every check must cite a SANS clause."""
        r = check(_spec(), _passing_sections())
        bad = [c.name for c in r.checks if not c.clause]
        assert bad == [], f"Checks missing clause: {bad}"

    def test_rules_version_populated(self):
        r = check(_spec(), _passing_sections())
        assert "SANS 10162-1" in r.rules_version

    def test_frame_spec_echoed_in_result(self):
        spec = _spec()
        r = check(spec, _passing_sections())
        assert r.frame_spec == spec


class TestCheckCorrectness:
    def test_passing_sections_gives_passed_true(self):
        """Sections chosen by design() must pass all checks in check() too."""
        r = check(_spec(), _passing_sections())
        failing = [c for c in r.checks if not c.passed]
        assert r.passed, (
            f"check() failed for design()-chosen sections:\n"
            + "\n".join(f"  {c.name}: util={c.utilisation:.3f}" for c in failing)
        )

    def test_undersized_sections_gives_passed_false(self):
        """The lightest sections in the library are too small for a 15 m frame."""
        r = check(_spec(), _tiny_sections())
        # At least the moment or interaction check should fail
        assert not r.passed, (
            "check() unexpectedly passed for the library's lightest section on a 15 m frame"
        )

    def test_undersized_still_returns_all_checks(self):
        """Even when sections fail, check() must return check results for every check."""
        r = check(_spec(), _tiny_sections())
        # We expect at least rafter + column strength checks + sway + deflection
        assert len(r.checks) >= 4

    def test_governing_utilisation_over_one_for_undersized(self):
        r = check(_spec(), _tiny_sections())
        assert r.governing_utilisation > 1.0

    def test_check_is_deterministic(self):
        """Same inputs → identical output (same guarantee as design())."""
        spec = _spec()
        sections = _passing_sections()
        r1 = check(spec, sections)
        r2 = check(spec, sections)
        import json
        assert json.dumps(r1.model_dump(mode="json"), sort_keys=True) == \
               json.dumps(r2.model_dump(mode="json"), sort_keys=True)


class TestCheckVsDesign:
    def test_check_with_design_sections_same_pass_fail(self):
        """check() with design()-chosen sections must agree on pass/fail for every check.

        Exact utilisation values may differ slightly because design() may have upgraded the
        rafter for deflection — changing self-weight and thus dead-load UDLs. What must be
        invariant is the pass/fail outcome: if design() passed all checks, check() with the
        same sections must also pass all checks.
        """
        spec = _spec()
        r_design = design(spec)
        r_check = check(spec, list(r_design.sections))

        design_outcomes = {c.name: c.passed for c in r_design.checks}
        check_outcomes  = {c.name: c.passed for c in r_check.checks}

        for name, passed_d in design_outcomes.items():
            assert name in check_outcomes, f"check() missing check {name!r}"
            assert check_outcomes[name] == passed_d, (
                f"Pass/fail mismatch for {name!r}: "
                f"design={passed_d} check={check_outcomes[name]}"
            )

    def test_check_with_design_sections_passes(self):
        """check() with design()-chosen sections must report passed=True."""
        spec = _spec()
        r_design = design(spec)
        r_check = check(spec, list(r_design.sections))
        failing = [c for c in r_check.checks if not c.passed]
        assert r_check.passed, (
            f"check() failed for design()-chosen sections:\n"
            + "\n".join(f"  {c.name}: util={c.utilisation:.3f}" for c in failing)
        )


# ---------------------------------------------------------------------------
# Part B: total_steel_mass_kg + indicative_cost_zar
# ---------------------------------------------------------------------------

class TestMassOnDesignResult:
    def test_design_result_has_mass(self):
        r = design(_spec())
        assert r.total_steel_mass_kg is not None

    def test_design_result_mass_positive(self):
        r = design(_spec())
        assert r.total_steel_mass_kg > 0

    def test_check_result_has_mass(self):
        r = check(_spec(), _passing_sections())
        assert r.total_steel_mass_kg is not None
        assert r.total_steel_mass_kg > 0

    def test_mass_formula_matches_sections(self):
        """Verify: mass = 2×rafter_half_len×raf_kg_m + 2×eaves_h×col_kg_m."""
        spec = _spec()
        r = design(spec)
        lib = SectionLibrary.load_default()
        secs = {s.member: lib.get(s.designation) for s in r.sections}
        geom = spec.geometry
        half_span_m = geom.span_m / 2.0
        rafter_half_len_m = math.hypot(
            half_span_m,
            geom.apex_height_m - geom.eaves_height_m,
        )
        expected_mass = (
            2.0 * rafter_half_len_m * secs["rafter"].mass_per_metre_kg_m
            + 2.0 * geom.eaves_height_m * secs["column"].mass_per_metre_kg_m
        )
        assert r.total_steel_mass_kg == pytest.approx(expected_mass, rel=1e-6)

    def test_heavier_frame_has_greater_mass(self):
        """Wider bay spacing → heavier sections → higher per-frame mass."""
        spec_narrow = FrameSpec(
            geometry=FrameGeometry(span_m=15, eaves_height_m=5, roof_pitch_deg=8,
                                   bay_spacing_m=3.0, number_of_bays=5),
            dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
            wind=WindContext(basic_wind_speed_ms=36, terrain_category=TerrainCategory.B),
        )
        r_narrow = design(spec_narrow)
        r_wide   = design(_spec())          # bay_spacing_m=6 → heavier
        # Heavier loading should produce heavier sections in at least one member
        assert r_wide.total_steel_mass_kg >= r_narrow.total_steel_mass_kg


class TestCostOnDesignResult:
    def test_design_result_has_cost(self):
        r = design(_spec())
        assert r.indicative_cost_zar is not None

    def test_cost_positive(self):
        r = design(_spec())
        assert r.indicative_cost_zar > 0

    def test_cost_default_rate_consistent_with_mass(self):
        """indicative_cost_zar = total_steel_mass_kg × default_rate (R20/kg)."""
        r = design(_spec())
        # Default rate is R20/kg = R20,000/tonne (configurable; see design.py)
        from torenone_kernel.design import DEFAULT_COST_RATE_ZAR_PER_KG
        assert r.indicative_cost_zar == pytest.approx(
            r.total_steel_mass_kg * DEFAULT_COST_RATE_ZAR_PER_KG, rel=1e-9
        )

    def test_check_custom_rate(self):
        """Passing a custom cost rate changes the cost proportionally."""
        spec = _spec()
        sections = _passing_sections()
        r1 = check(spec, sections, cost_rate_zar_per_kg=20.0)
        r2 = check(spec, sections, cost_rate_zar_per_kg=30.0)
        assert r2.indicative_cost_zar == pytest.approx(
            r1.indicative_cost_zar * 1.5, rel=1e-9
        )

    def test_design_custom_rate(self):
        """design() also accepts a custom cost rate."""
        spec = _spec()
        r1 = design(spec, cost_rate_zar_per_kg=20.0)
        r2 = design(spec, cost_rate_zar_per_kg=40.0)
        assert r2.indicative_cost_zar == pytest.approx(
            r1.indicative_cost_zar * 2.0, rel=1e-9
        )
