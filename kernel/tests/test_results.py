"""Contract tests for the kernel's result models (Task 1.1 — result contracts).

These are pure structural contracts: identity, references, and aggregation logic. NO engineering
values are asserted here (those arrive with the SANS modules, validated against worked examples).
The one piece of logic exercised is safety-relevant aggregation: a DesignResult must NOT report
`passed` when it has no checks (a vacuous pass would be dangerous).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from torenone_kernel import rules_version
from torenone_kernel.models import (
    AnalysisResult,
    CheckResult,
    DeadLoadInputs,
    DesignResult,
    FrameGeometry,
    FrameSpec,
    LimitState,
    LoadCase,
    LoadCombination,
    LoadType,
    MemberForces,
    SectionChoice,
    TerrainCategory,
    WindContext,
)


def _frame() -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=24.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0, number_of_bays=7
        ),
        dead=DeadLoadInputs(roof_kpa=0.15),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
    )


def _check(name: str, passed: bool, utilisation: float) -> CheckResult:
    return CheckResult(name=name, clause="SANS 10162-1 cl. X", utilisation=utilisation, passed=passed)


def _design(checks: list[CheckResult]) -> DesignResult:
    return DesignResult(
        frame_spec=_frame(),
        sections=[SectionChoice(member="rafter", designation="IPE 400")],
        checks=checks,
        rules_version=rules_version.as_dict(),
    )


# --- Loads & combinations ---------------------------------------------------


def test_load_case_and_combination_reference_cases() -> None:
    dead = LoadCase(name="DL", load_type=LoadType.DEAD)
    wind = LoadCase(name="WL", load_type=LoadType.WIND)
    combo = LoadCombination(
        name="ULS-1", limit_state=LimitState.ULS, factors={dead.name: 1.2, wind.name: 0.6}
    )
    assert set(combo.referenced_cases) == {"DL", "WL"}


def test_combination_requires_at_least_one_factor() -> None:
    with pytest.raises(ValidationError):
        LoadCombination(name="empty", limit_state=LimitState.ULS, factors={})


# --- Analysis ---------------------------------------------------------------


def test_analysis_result_requires_forces() -> None:
    AnalysisResult(
        combination="ULS-1",
        forces=[MemberForces(location="apex", axial_kn=10.0, shear_kn=5.0, moment_knm=20.0)],
    )
    with pytest.raises(ValidationError):
        AnalysisResult(combination="ULS-1", forces=[])


# --- Checks -----------------------------------------------------------------


def test_check_result_requires_a_clause_reference() -> None:
    # PRD FR-18: every reported check must cite its code clause.
    with pytest.raises(ValidationError):
        CheckResult(name="moment", clause="", utilisation=0.5, passed=True)


def test_check_utilisation_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        CheckResult(name="moment", clause="cl. 13", utilisation=-0.1, passed=True)


# --- DesignResult aggregation (safety-relevant) -----------------------------


def test_design_passes_only_when_all_checks_pass() -> None:
    assert _design([_check("a", True, 0.8), _check("b", True, 0.9)]).passed is True
    assert _design([_check("a", True, 0.8), _check("b", False, 1.2)]).passed is False


def test_design_with_no_checks_does_not_vacuously_pass() -> None:
    # A result with zero checks must never report passed=True.
    assert _design([]).passed is False


def test_governing_utilisation_is_the_max() -> None:
    d = _design([_check("a", True, 0.42), _check("b", True, 0.97), _check("c", True, 0.51)])
    assert d.governing_utilisation == pytest.approx(0.97)


def test_design_carries_pinned_rules_version() -> None:
    d = _design([_check("a", True, 0.8)])
    assert "SANS 10162-1" in d.rules_version


def test_design_result_is_immutable() -> None:
    d = _design([_check("a", True, 0.8)])
    with pytest.raises(ValidationError):
        d.warnings = ("tampered",)  # type: ignore[misc]


def test_warnings_default_empty() -> None:
    assert _design([_check("a", True, 0.8)]).warnings == ()
