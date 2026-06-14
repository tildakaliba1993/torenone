"""Benchmark cases for the Phase 8 validation gate (Tasks 8.1 / 8.2).

THIS IS WHERE YOUR CO-FOUNDER'S REAL PAST DESIGNS GO.

To add a benchmark you only fill in plain numbers — no code knowledge needed.
Copy the template at the bottom into the ``BENCHMARKS`` list and replace the
values with a real portal frame your firm actually designed (and its original,
hand/established-software results). The test in ``test_validation.py`` then runs
it through TorenOne's kernel and checks the answers match.

See ``docs/VALIDATION_GUIDE.md`` for the step-by-step, non-technical walkthrough.
"""

from __future__ import annotations

from dataclasses import dataclass

from torenone_kernel.models.enums import SteelGrade, TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FoundationInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    Materials,
    Restraints,
    WindContext,
)


def make_spec(
    *,
    # --- Geometry ---
    span_m: float,
    eaves_height_m: float,
    roof_pitch_deg: float,
    bay_spacing_m: float,
    number_of_bays: int,
    # --- Loads ---
    roof_dead_kpa: float,
    basic_wind_speed_ms: float,
    terrain_category: str,  # "A" | "B" | "C" | "D"
    services_kpa: float = 0.0,
    wall_cladding_kpa: float = 0.0,
    roof_access: bool = False,
    site_altitude_m: float = 0.0,
    has_dominant_opening: bool = False,
    # --- Material / foundation ---
    steel_grade: str = "S355JR",  # "S275JR" | "S355JR"
    allowable_bearing_kpa: float | None = None,
    concrete_fcu_mpa: float = 25.0,
    # --- Optional lateral restraints (None => unrestrained, conservative) ---
    rafter_restraint_m: float | None = None,
    column_restraint_m: float | None = None,
) -> FrameSpec:
    """Build a FrameSpec from plain numbers — the inputs an engineer reads off a drawing."""
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=span_m,
            eaves_height_m=eaves_height_m,
            roof_pitch_deg=roof_pitch_deg,
            bay_spacing_m=bay_spacing_m,
            number_of_bays=number_of_bays,
        ),
        materials=Materials(steel_grade=SteelGrade(steel_grade)),
        restraints=Restraints(
            rafter_restraint_spacing_m=rafter_restraint_m,
            column_restraint_spacing_m=column_restraint_m,
        ),
        dead=DeadLoadInputs(
            roof_kpa=roof_dead_kpa,
            services_kpa=services_kpa,
            wall_cladding_kpa=wall_cladding_kpa,
        ),
        imposed=ImposedLoadInputs(roof_access=roof_access),
        wind=WindContext(
            basic_wind_speed_ms=basic_wind_speed_ms,
            terrain_category=TerrainCategory(terrain_category),
            site_altitude_m=site_altitude_m,
            has_dominant_opening=has_dominant_opening,
        ),
        foundation=FoundationInputs(
            allowable_bearing_kpa=allowable_bearing_kpa,
            concrete_fcu_mpa=concrete_fcu_mpa,
        ),
    )


@dataclass(frozen=True)
class BenchmarkCase:
    """One real past design + its original answers, with the tolerances you agree on."""

    name: str  # e.g. "Pretoria warehouse, 2021"
    source: str  # where the original came from (project ref, engineer, software)
    spec: FrameSpec  # the frame inputs (use make_spec(...))

    # The original design's member sizes (SAISC designations, e.g. "457x191x67").
    original_rafter: str
    original_column: str

    # Optional original results the engineer recorded (leave None to skip that check):
    expected_governing_utilisation: float | None = None
    expected_steel_mass_kg: float | None = None

    # Agreed tolerances (your co-founder decides what "close enough" means):
    utilisation_abs_tol: float = 0.10  # ± on a 0–1 utilisation ratio
    mass_rel_tol: float = 0.15  # ± fraction on steel mass
    notes: str = ""


# ---------------------------------------------------------------------------
# Add real cases here. While this list is empty the validation gate SKIPS
# (so CI stays green) — once you add a case it becomes a hard, must-pass test.
# ---------------------------------------------------------------------------
BENCHMARKS: list[BenchmarkCase] = []


# ---------------------------------------------------------------------------
# TEMPLATE — copy this into BENCHMARKS above and replace every value with the
# real numbers from a past project. Delete the leading "# " on each line.
# ---------------------------------------------------------------------------
#
# BENCHMARKS = [
#     BenchmarkCase(
#         name="Pretoria warehouse (2021)",
#         source="Project 2021-114, designed by <engineer> in <software>",
#         spec=make_spec(
#             span_m=24.0,
#             eaves_height_m=7.0,
#             roof_pitch_deg=7.0,
#             bay_spacing_m=6.0,
#             number_of_bays=8,
#             roof_dead_kpa=0.20,
#             basic_wind_speed_ms=36.0,
#             terrain_category="B",
#             allowable_bearing_kpa=200.0,
#         ),
#         original_rafter="457x191x67",   # the rafter size actually used
#         original_column="457x191x82",   # the column size actually used
#         expected_governing_utilisation=0.86,   # optional: the original's governing ratio
#         expected_steel_mass_kg=None,           # optional: per-frame steel mass (kg)
#         utilisation_abs_tol=0.10,
#         mass_rel_tol=0.15,
#         notes="Most typical shed we do. Confirm wind speed off the SANS map.",
#     ),
# ]
