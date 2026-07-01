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

# Practice range for a single portal SPAN (m). Only bounds which width-splits we OFFER — every
# option is still fully designed + checked. Splitting a wide building into more spans trades lighter
# rafters/columns for extra internal-column lines; total steel has a real optimum. PROVISIONAL: any
# option with >1 span uses the multi-span (D13) path, pending engineer validation.
MIN_SPAN_M: float = 8.0
MAX_SPAN_M: float = 40.0
MAX_SPAN_OPTIONS: int = 5


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


@dataclasses.dataclass(frozen=True)
class SpanSplitOption:
    """One way to split the building WIDTH: a span count + per-span width, designed and costed."""

    number_of_spans: int
    span_m: float               # per-span width
    number_of_frames: int       # portal frames along the length (= number_of_bays + 1)
    feasible: bool
    per_frame_mass_kg: float | None
    total_primary_mass_kg: float | None
    passed: bool
    governing_utilisation: float
    is_baseline: bool
    provisional: bool           # True for any multi-span option (D13)
    result: DesignResult | None


@dataclasses.dataclass(frozen=True)
class SpanSplitComparison:
    building_width_m: float
    baseline: SpanSplitOption
    options: tuple[SpanSplitOption, ...]  # includes the baseline; sorted by total primary steel
    lightest_passing: SpanSplitOption | None
    notes: tuple[str, ...]


def enumerate_span_counts(
    building_width_m: float,
    *,
    min_span_m: float = MIN_SPAN_M,
    max_span_m: float = MAX_SPAN_M,
) -> list[tuple[int, float]]:
    """Span counts whose equal split of ``building_width_m`` lies in the offered per-span range."""
    if building_width_m <= 0:
        return []
    n_min = max(1, math.ceil(building_width_m / max_span_m - 1e-9))
    n_max = max(1, math.floor(building_width_m / min_span_m + 1e-9))
    return [(n, building_width_m / n) for n in range(n_min, n_max + 1)]


def _with_spans(spec: FrameSpec, number_of_spans: int, span_m: float) -> FrameSpec:
    new_geom = spec.geometry.model_copy(
        update={"number_of_spans": number_of_spans, "span_m": span_m}
    )
    return spec.model_copy(update={"geometry": new_geom})


def compare_span_splits(
    spec: FrameSpec,
    *,
    cost_rate_zar_per_kg: float = DEFAULT_COST_RATE_ZAR_PER_KG,
    code: DesignCode = DEFAULT_CODE,
    min_span_m: float = MIN_SPAN_M,
    max_span_m: float = MAX_SPAN_M,
    max_options: int = MAX_SPAN_OPTIONS,
) -> SpanSplitComparison:
    """Design every sensible split of the building's WIDTH into equal spans; rank by total steel.

    Holds the overall roofed width fixed (``span_m × number_of_spans``) and varies the number of
    internal column lines — the real "clear-span vs multi-span" topology choice. The input's own
    split is always the ``baseline``. Any option with >1 span is PROVISIONAL (multi-span, D13).
    Duopitch only; a mono-pitch spec returns just its (single-span) baseline. Deterministic.
    """
    width_m = spec.geometry.building_width_m
    base_spans = spec.geometry.number_of_spans

    counts: dict[int, float] = {}
    if spec.geometry.roof_type != "monopitch":
        counts = dict(enumerate_span_counts(width_m, min_span_m=min_span_m, max_span_m=max_span_m))
    counts.setdefault(base_spans, spec.geometry.span_m)

    ordered = sorted(counts.items())
    if len(ordered) > max_options:
        keep = {0, len(ordered) - 1} | {i for i, (n, _) in enumerate(ordered) if n == base_spans}
        for i in range(len(ordered)):
            if len(keep) >= max_options:
                break
            keep.add(i)
        ordered = [ordered[i] for i in sorted(keep)]

    n_frames = spec.geometry.number_of_bays + 1
    options: list[SpanSplitOption] = []
    for n, span in ordered:
        try:
            result: DesignResult | None = design(
                _with_spans(spec, n, span), cost_rate_zar_per_kg, code=code
            )
        except (NoSectionFoundError, SectionIneligibleError):
            result = None
        per_frame = result.total_steel_mass_kg if result is not None else None
        total = per_frame * n_frames if per_frame is not None else None
        options.append(
            SpanSplitOption(
                number_of_spans=n, span_m=span, number_of_frames=n_frames,
                feasible=result is not None,
                per_frame_mass_kg=per_frame, total_primary_mass_kg=total,
                passed=result.passed if result is not None else False,
                governing_utilisation=result.governing_utilisation if result is not None else 0.0,
                is_baseline=(n == base_spans), provisional=(n > 1), result=result,
            )
        )

    baseline = next(o for o in options if o.is_baseline)
    options.sort(key=lambda o: o.total_primary_mass_kg if o.total_primary_mass_kg is not None else math.inf)
    passing = [o for o in options if o.passed and o.total_primary_mass_kg is not None]
    lightest_passing = passing[0] if passing else None

    notes = [
        "Total steel compares the PRIMARY frames only (all columns + rafters × number of frames). "
        "Secondary steel, valley gutters and the extra internal-column foundations are not included.",
        f"Splits the {width_m:.1f} m width into equal spans in the {min_span_m:g}–{max_span_m:g} m "
        "range (a practice guide, not a code limit).",
    ]
    if any(o.provisional for o in options):
        notes.append(
            "Any option with more than one span is MULTI-SPAN — PROVISIONAL (D13), gravity-designed, "
            "wind + last mile not yet modelled; needs registered-engineer validation before use."
        )
    if any(not o.feasible for o in options):
        notes.append("Some splits have no adequate section (marked infeasible).")

    return SpanSplitComparison(
        building_width_m=width_m,
        baseline=baseline,
        options=tuple(options),
        lightest_passing=lightest_passing,
        notes=tuple(notes),
    )


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
