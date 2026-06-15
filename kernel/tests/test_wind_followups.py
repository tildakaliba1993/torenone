"""Wind follow-ups — SLS-2 wind sway (advisory) + auto-size-for-wind flag.

Covers the two wind follow-up deliverables on top of Part B:
  1. The SLS-2 eaves wind-sway (lateral drift) check, reported as an INFORMATIONAL
     (advisory-only, non-gating) CheckResult in both design() and check().
  2. The `design(autosize_for_wind=...)` flag — OFF by default (gravity sizes, wind only
     CHECKED); when ON, members are sized for the gravity+wind envelope so the gating
     ULS-2/3 wind checks pass.

Both rest on the PROVISIONAL wind-on-frame model (sign conventions pending co-founder
validation) — these tests assert the WIRING + semantics, not the SANS magnitudes.
"""

from __future__ import annotations

import pytest
from torenone_kernel.design import check, design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import CheckResult, DesignResult, SectionChoice
from torenone_kernel.rules_version import as_dict as _rules_version


def _spec() -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


def _wind_governed_spec() -> FrameSpec:
    # Tall, light, high-wind frame: gravity-sized members FAIL the ULS-2/3 wind checks
    # (verified empirically — ULS-wind util ~2.5 with the flag off).
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=20.0, eaves_height_m=8.0, roof_pitch_deg=10.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.10),
        wind=WindContext(basic_wind_speed_ms=50.0, terrain_category=TerrainCategory.A),
    )


def _sway_check(checks: list[CheckResult]) -> CheckResult:
    matches = [c for c in checks if "[SLS-2 wind]" in c.name]
    assert len(matches) == 1, f"expected exactly one SLS-2 sway check, got {len(matches)}"
    return matches[0]


def _uls_wind_utils(r: DesignResult) -> list[float]:
    return [
        c.utilisation
        for c in r.checks
        if "[ULS-" in c.name and "wind]" in c.name and not c.informational
    ]


# ---------------------------------------------------------------------------
# 1. SLS-2 wind sway — advisory (informational, non-gating)
# ---------------------------------------------------------------------------


class TestSlsWindSway:
    def test_design_reports_sls2_sway_as_informational(self) -> None:
        sway = _sway_check(design(_spec()).checks)
        assert sway.informational is True
        assert "Annex D" in sway.clause
        assert "H/400" in sway.clause or "H/400" in sway.name

    def test_check_mode_reports_sls2_sway_as_informational(self) -> None:
        sections = [
            SectionChoice(member="rafter", designation="305x165x54"),
            SectionChoice(member="column", designation="305x165x54"),
        ]
        sway = _sway_check(check(_spec(), sections).checks)
        assert sway.informational is True

    def test_sway_does_not_gate_passed_or_governing(self) -> None:
        # The standard frame fails H/400 sway badly (util > 1) but, being advisory-only,
        # it must NOT fail the design nor inflate the governing utilisation.
        r = design(_spec())
        sway = _sway_check(r.checks)
        assert sway.utilisation > 1.0          # it genuinely exceeds H/400
        assert sway.passed is False
        assert r.passed is True                # design still passes (gating checks only)
        assert r.governing_utilisation < sway.utilisation
        gating_max = max(c.utilisation for c in r.checks if not c.informational)
        assert r.governing_utilisation == pytest.approx(gating_max)


# ---------------------------------------------------------------------------
# 2. Auto-size for wind (flag, OFF by default)
# ---------------------------------------------------------------------------


class TestAutosizeForWind:
    def test_default_is_off(self) -> None:
        # Omitting the flag is identical to passing it False.
        assert design(_spec()).model_dump() == design(_spec(), autosize_for_wind=False).model_dump()

    def test_off_leaves_a_wind_governed_frame_failing_uls_wind(self) -> None:
        r = design(_wind_governed_spec())  # flag OFF
        assert max(_uls_wind_utils(r)) > 1.0    # wind governs and is reported as failing

    def test_on_sizes_for_wind_so_uls_wind_checks_pass(self) -> None:
        off = design(_wind_governed_spec())
        on = design(_wind_governed_spec(), autosize_for_wind=True)
        # Sizing for the wind envelope makes every gating ULS-2/3 wind check pass...
        assert max(_uls_wind_utils(on)) <= 1.0 + 1e-9
        # ...at the cost of heavier (never lighter) steel than the gravity-only sizing.
        assert on.total_steel_mass_kg >= off.total_steel_mass_kg
        assert on.total_steel_mass_kg > off.total_steel_mass_kg  # this frame genuinely grows

    def test_on_is_deterministic(self) -> None:
        a = design(_wind_governed_spec(), autosize_for_wind=True)
        b = design(_wind_governed_spec(), autosize_for_wind=True)
        assert a.model_dump() == b.model_dump()


# ---------------------------------------------------------------------------
# 3. Informational-check semantics on DesignResult (the gating contract)
# ---------------------------------------------------------------------------


class TestInformationalSemantics:
    def _result(self, checks: list[CheckResult]) -> DesignResult:
        return DesignResult(
            frame_spec=_spec(),
            sections=[
                SectionChoice(member="rafter", designation="IPE 200"),
                SectionChoice(member="column", designation="IPE 200"),
            ],
            checks=checks,
            rules_version=_rules_version(),
        )

    def test_failing_informational_check_does_not_fail_the_design(self) -> None:
        r = self._result([
            CheckResult(name="strength", clause="cl.13", utilisation=0.5, passed=True),
            CheckResult(
                name="advisory", clause="Annex D", utilisation=3.0,
                passed=False, informational=True,
            ),
        ])
        assert r.passed is True
        assert r.governing_utilisation == pytest.approx(0.5)

    def test_gating_failure_still_fails(self) -> None:
        r = self._result([
            CheckResult(name="strength", clause="cl.13", utilisation=1.2, passed=False),
            CheckResult(
                name="advisory", clause="Annex D", utilisation=0.1,
                passed=True, informational=True,
            ),
        ])
        assert r.passed is False
        assert r.governing_utilisation == pytest.approx(1.2)

    def test_only_informational_checks_never_vacuously_passes(self) -> None:
        # SAFETY: a design with no GATING checks must not report a pass.
        r = self._result([
            CheckResult(
                name="advisory", clause="Annex D", utilisation=0.1,
                passed=True, informational=True,
            ),
        ])
        assert r.passed is False
