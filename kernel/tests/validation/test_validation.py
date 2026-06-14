"""Phase 8 validation gate (Task 8.2) — THE must-pass correctness test.

Each real benchmark in ``benchmarks.BENCHMARKS`` is run through the kernel and
asserted to reproduce the original engineer's design within the agreed
tolerances (PRD NFR-1). While the list is empty the gate SKIPS (CI stays green);
add one real case and it becomes a hard, must-pass test.

Two things run here:
  * ``test_validation_gate`` — the real gate, one parametrised case per benchmark.
  * ``test_harness_self_check`` — proves the harness machinery works (a design fed
    its own results passes), so the scaffold is trustworthy before any real data.
"""

from __future__ import annotations

import pytest
from benchmarks import BENCHMARKS, BenchmarkCase, make_spec
from torenone_kernel.design import check, design
from torenone_kernel.models.results import DesignResult, SectionChoice


def _report(case: BenchmarkCase, checked: DesignResult, autosized: DesignResult) -> str:
    chosen = ", ".join(f"{s.member}={s.designation}" for s in autosized.sections)
    return (
        f"\n--- Validation report: {case.name} ({case.source}) ---\n"
        f"Original sections:  rafter={case.original_rafter}, column={case.original_column}\n"
        f"  CHECK mode  -> governing {checked.governing_utilisation:.2f}, "
        f"passed={checked.passed}, mass={checked.total_steel_mass_kg} kg\n"
        f"Kernel auto-size:   {chosen}\n"
        f"  DESIGN mode -> governing {autosized.governing_utilisation:.2f}, "
        f"passed={autosized.passed}, mass={autosized.total_steel_mass_kg} kg\n"
    )


def run_validation(case: BenchmarkCase) -> str:
    """Validate one case; raise AssertionError (with a readable report) on mismatch."""
    original_sections = [
        SectionChoice(member="rafter", designation=case.original_rafter),
        SectionChoice(member="column", designation=case.original_column),
    ]
    checked = check(case.spec, original_sections)
    autosized = design(case.spec)
    report = _report(case, checked, autosized)

    # 1) The engineer's ACTUAL, built design must be adequate per the kernel.
    assert checked.governing_utilisation <= 1.0 + case.utilisation_abs_tol, (
        f"Kernel says the ORIGINAL design is overstressed "
        f"(governing {checked.governing_utilisation:.2f} > 1.0 + tol). Investigate.{report}"
    )

    # 2) Optional — match the original's recorded governing utilisation.
    if case.expected_governing_utilisation is not None:
        diff = abs(checked.governing_utilisation - case.expected_governing_utilisation)
        assert diff <= case.utilisation_abs_tol, (
            f"Governing utilisation {checked.governing_utilisation:.2f} differs from the "
            f"original {case.expected_governing_utilisation:.2f} by more than "
            f"±{case.utilisation_abs_tol:.2f}.{report}"
        )

    # 3) Optional — match the original's per-frame steel mass.
    if case.expected_steel_mass_kg is not None and checked.total_steel_mass_kg is not None:
        rel = abs(checked.total_steel_mass_kg - case.expected_steel_mass_kg) / case.expected_steel_mass_kg
        assert rel <= case.mass_rel_tol, (
            f"Steel mass {checked.total_steel_mass_kg:.0f} kg differs from the original "
            f"{case.expected_steel_mass_kg:.0f} kg by more than ±{case.mass_rel_tol:.0%}.{report}"
        )

    # 4) The kernel's own auto-sizing must produce a passing design.
    assert autosized.passed, (
        f"Kernel auto-size produced a FAILING design "
        f"(governing {autosized.governing_utilisation:.2f}).{report}"
    )
    return report


@pytest.mark.skipif(
    not BENCHMARKS,
    reason=(
        "No benchmark cases yet — add a real past design in benchmarks.py "
        "(see docs/VALIDATION_GUIDE.md). THIS is the Phase 8 validation gate."
    ),
)
@pytest.mark.parametrize("case", BENCHMARKS, ids=[c.name for c in BENCHMARKS])
def test_validation_gate(case: BenchmarkCase) -> None:
    run_validation(case)


def test_harness_self_check() -> None:
    """A design fed its own results back must pass — proves the harness logic works."""
    spec = make_spec(
        span_m=20.0,
        eaves_height_m=6.0,
        roof_pitch_deg=10.0,
        bay_spacing_m=6.0,
        number_of_bays=5,
        roof_dead_kpa=0.15,
        basic_wind_speed_ms=36.0,
        terrain_category="B",
        allowable_bearing_kpa=150.0,
    )
    autosized = design(spec)
    rafter = next(s.designation for s in autosized.sections if s.member == "rafter")
    column = next(s.designation for s in autosized.sections if s.member == "column")

    case = BenchmarkCase(
        name="harness self-check",
        source="kernel auto-size (synthetic)",
        spec=spec,
        original_rafter=rafter,
        original_column=column,
        expected_governing_utilisation=autosized.governing_utilisation,
        expected_steel_mass_kg=autosized.total_steel_mass_kg,
    )
    report = run_validation(case)
    assert "harness self-check" in report
