"""Bay-layout exploration — "how should this building be framed?" (topology, Path A).

Given a validated :class:`FrameSpec`, this enumerates the sensible ways to frame the SAME building
(the same overall length + envelope) with a different number of portal frames, designs EACH through
the existing, validated :func:`design` pipeline, and reports the total primary steel of each so the
engineer can pick the most economical layout.

Company-law posture (🟢): this introduces **no new engineering number or method**. Every capacity,
utilisation, mass and pass/fail comes back from the unchanged, Red-Book/textbook-validated ``design``
pipeline. The candidate bay spacings are ordinary geometric inputs (the same ones a user types by
hand); the offered spacing range is a documented *practice* heuristic for what to present, not a code
limit; and the "total primary steel" figure is plain arithmetic on kernel outputs
(per-frame mass × number of frames). Options are presented — the engineer confirms one. Same posture
as the agentic design loop.

Scope note (honest): the comparison covers the **primary portal frames only**. Secondary steel
(purlins/girts) and connection steel are not in the figure — they trade off in the opposite direction
to frame count, so the comparison is a sound first-order economic guide, not a full bill of steel.
"""

from __future__ import annotations

import dataclasses
import math

from torenone_kernel.checks.autosize import NoSectionFoundError, SectionIneligibleError
from torenone_kernel.codes import DEFAULT_CODE
from torenone_kernel.codes.base import DesignCode
from torenone_kernel.design import DEFAULT_COST_RATE_ZAR_PER_KG, design
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import DesignResult

# Documented practice range for portal-frame bay spacing in SA steel buildings. This only bounds
# which layouts we *offer* for comparison — it is NOT an engineering limit (every option is still
# fully designed and checked by the kernel). Wide enough to surface the real economic trade-off.
MIN_BAY_SPACING_M: float = 4.5
MAX_BAY_SPACING_M: float = 9.0
# Bound the compute / choice count regardless of building length.
MAX_LAYOUT_OPTIONS: int = 6


@dataclasses.dataclass(frozen=True)
class BayLayoutOption:
    """One way to frame the building: a bay count + spacing, fully designed and costed."""

    number_of_bays: int
    bay_spacing_m: float
    number_of_frames: int  # portal frames = number_of_bays + 1
    feasible: bool  # False if no section could carry this spacing (design found nothing)
    per_frame_mass_kg: float | None
    total_primary_mass_kg: float | None  # per_frame_mass × number_of_frames
    passed: bool
    governing_utilisation: float
    is_baseline: bool
    result: DesignResult | None


@dataclasses.dataclass(frozen=True)
class BayLayoutComparison:
    """The set of framing options for one building, plus the baseline and the lightest that passes."""

    building_length_m: float
    baseline: BayLayoutOption
    options: tuple[BayLayoutOption, ...]  # includes the baseline; sorted by total primary steel
    lightest_passing: BayLayoutOption | None
    notes: tuple[str, ...]


def enumerate_bay_counts(
    building_length_m: float,
    *,
    min_bay_m: float = MIN_BAY_SPACING_M,
    max_bay_m: float = MAX_BAY_SPACING_M,
) -> list[tuple[int, float]]:
    """Bay counts whose *uniform* spacing tiles ``building_length_m`` within the offered range.

    For ``n`` bays the spacing is ``L / n``; we keep every ``n`` for which that spacing lies in
    ``[min_bay_m, max_bay_m]``. Returned ascending by bay count (→ descending spacing).
    """
    if building_length_m <= 0:
        return []
    # spacing = L/n ≤ max  ⟹  n ≥ L/max ;  spacing ≥ min  ⟹  n ≤ L/min
    n_min = max(1, math.ceil(building_length_m / max_bay_m - 1e-9))
    n_max = math.floor(building_length_m / min_bay_m + 1e-9)
    return [(n, building_length_m / n) for n in range(n_min, n_max + 1)]


def _with_layout(spec: FrameSpec, number_of_bays: int, bay_spacing_m: float) -> FrameSpec:
    """A copy of *spec* re-framed with a different bay count + spacing (same building otherwise)."""
    new_geom = spec.geometry.model_copy(
        update={"number_of_bays": number_of_bays, "bay_spacing_m": bay_spacing_m}
    )
    return spec.model_copy(update={"geometry": new_geom})


def compare_bay_layouts(
    spec: FrameSpec,
    *,
    cost_rate_zar_per_kg: float = DEFAULT_COST_RATE_ZAR_PER_KG,
    code: DesignCode = DEFAULT_CODE,
    min_bay_m: float = MIN_BAY_SPACING_M,
    max_bay_m: float = MAX_BAY_SPACING_M,
    max_options: int = MAX_LAYOUT_OPTIONS,
) -> BayLayoutComparison:
    """Design every sensible framing of *spec*'s building and rank them by total primary steel.

    The input's own layout is always included as the ``baseline`` (even if its spacing sits outside
    the offered range — we never silently drop what the engineer specified). Deterministic: identical
    inputs → identical output (sorted candidates, deterministic ``design``).
    """
    length_m = spec.geometry.building_length_m
    base_bays = spec.geometry.number_of_bays

    # Candidate bay counts: the practice range, plus the input's own (as baseline).
    counts: dict[int, float] = {n: spacing for n, spacing in enumerate_bay_counts(
        length_m, min_bay_m=min_bay_m, max_bay_m=max_bay_m
    )}
    counts.setdefault(base_bays, spec.geometry.bay_spacing_m)

    # Bound the option count, but always keep the baseline and the extreme spacings (the ends carry
    # the real trade-off). Trim from the middle if needed.
    ordered = sorted(counts.items())  # ascending bay count
    if len(ordered) > max_options:
        keep_idx = {0, len(ordered) - 1}
        keep_idx |= {i for i, (n, _) in enumerate(ordered) if n == base_bays}
        for i in range(len(ordered)):  # fill the rest evenly until we hit the cap
            if len(keep_idx) >= max_options:
                break
            keep_idx.add(i)
        ordered = [ordered[i] for i in sorted(keep_idx)]

    options: list[BayLayoutOption] = []
    for n, spacing in ordered:
        try:
            result: DesignResult | None = design(
                _with_layout(spec, n, spacing), cost_rate_zar_per_kg, code=code
            )
        except (NoSectionFoundError, SectionIneligibleError):
            # This spacing is too demanding for any available section — a real, useful outcome
            # (that layout is infeasible), not an error. Surface it rather than dropping it.
            result = None
        if result is None:
            options.append(
                BayLayoutOption(
                    number_of_bays=n, bay_spacing_m=spacing, number_of_frames=n + 1,
                    feasible=False, per_frame_mass_kg=None, total_primary_mass_kg=None,
                    passed=False, governing_utilisation=0.0,
                    is_baseline=(n == base_bays), result=None,
                )
            )
            continue
        per_frame = result.total_steel_mass_kg
        total = per_frame * (n + 1) if per_frame is not None else None
        options.append(
            BayLayoutOption(
                number_of_bays=n,
                bay_spacing_m=spacing,
                number_of_frames=n + 1,
                feasible=True,
                per_frame_mass_kg=per_frame,
                total_primary_mass_kg=total,
                passed=result.passed,
                governing_utilisation=result.governing_utilisation,
                is_baseline=(n == base_bays),
                result=result,
            )
        )

    baseline = next(o for o in options if o.is_baseline)

    # Sort by total primary steel (lightest first); unknown masses sink to the bottom.
    def _mass_key(o: BayLayoutOption) -> float:
        return o.total_primary_mass_kg if o.total_primary_mass_kg is not None else math.inf

    options.sort(key=_mass_key)

    passing = [o for o in options if o.passed and o.total_primary_mass_kg is not None]
    lightest_passing = passing[0] if passing else None

    notes: list[str] = [
        "Total steel compares the PRIMARY portal frames only (columns + rafters × number of frames). "
        "Secondary steel (purlins/girts) and connections are not included — confirm the full economy "
        "with a fabricator.",
        f"Bay spacings tile the {length_m:.1f} m building length exactly; the offered range is "
        f"{min_bay_m:g}–{max_bay_m:g} m (a practice guide, not a code limit).",
    ]
    if any(o.result is not None and o.result.warnings for o in options):
        notes.append(
            "One or more options carry design warnings (e.g. PROVISIONAL paths) — see each option."
        )
    if any(not o.feasible for o in options):
        notes.append(
            "Some spacings have no adequate section in the library (marked infeasible) — the frame "
            "would need to be closer-spaced or the geometry revised."
        )

    return BayLayoutComparison(
        building_length_m=length_m,
        baseline=baseline,
        options=tuple(options),
        lightest_passing=lightest_passing,
        notes=tuple(notes),
    )
