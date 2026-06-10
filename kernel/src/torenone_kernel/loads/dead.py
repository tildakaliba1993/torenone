"""Characteristic permanent (dead) loads on the portal frame (PRD FR-5).

Code-agnostic physics: member self-weight (mass × g) plus permanent area loads distributed over
the tributary width of a typical internal frame. SANS partial factors are applied later, at the
load-combination stage (SANS 10160-1, Task 1.7) — not here.

Sign convention / assumptions (surfaced in the report's assumptions block, FR-27):
  - Roof area loads (`roof_kpa`, `services_kpa`) are taken per m² of roof surface and applied as a
    UDL along the rafter over the tributary width.
  - Tributary width = frame spacing (`bay_spacing_m`) — the typical internal frame (worst case).
  - Self-weight uses g = 9.81 m/s² to convert section mass (kg/m) to weight (kN/m).
"""

from __future__ import annotations

from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import DeadLoadResult
from torenone_kernel.sections.properties import SectionProperties

GRAVITY_M_S2 = 9.81  # standard gravitational acceleration


def _self_weight_kn_per_m(mass_kg_per_m: float) -> float:
    """Convert section mass (kg/m) to self-weight (kN/m)."""
    return mass_kg_per_m * GRAVITY_M_S2 / 1000.0


def dead_loads(
    spec: FrameSpec,
    rafter: SectionProperties,
    column: SectionProperties,
) -> DeadLoadResult:
    """Compute characteristic dead loads for the given frame and member sections."""
    tributary_m = spec.geometry.bay_spacing_m
    roof_area_kpa = spec.dead.roof_kpa + spec.dead.services_kpa
    rafter_sw = _self_weight_kn_per_m(rafter.mass_per_metre_kg_m)

    return DeadLoadResult(
        roof_area_load_kpa=roof_area_kpa,
        tributary_width_m=tributary_m,
        rafter_self_weight_kn_per_m=rafter_sw,
        rafter_udl_kn_per_m=roof_area_kpa * tributary_m + rafter_sw,
        column_self_weight_kn_per_m=_self_weight_kn_per_m(column.mass_per_metre_kg_m),
        wall_cladding_udl_kn_per_m=spec.dead.wall_cladding_kpa * tributary_m,
    )
