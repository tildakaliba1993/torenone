"""Bay-layout exploration tests (topology, Path A) — torenone_kernel.layout.

Proves the generate-and-compare engine: it re-frames the SAME building with different bay counts,
designs each through the real pipeline, and ranks by total primary steel — introducing no new
engineering number (every figure comes back from design()).

Run:
    PYTHONPATH="kernel/src:tools" .venv/bin/pytest kernel/tests/test_layout.py -q
"""

from __future__ import annotations

from torenone_kernel.layout import (
    BayLayoutComparison,
    compare_bay_layouts,
    compare_span_splits,
    enumerate_bay_counts,
    enumerate_span_counts,
)
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    Restraints,
    WindContext,
)


def _spec(*, bay_spacing_m: float = 6.0, number_of_bays: int = 5) -> FrameSpec:
    """15 m span, 5 m eaves, 8° pitch — a comfortably designable frame."""
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=bay_spacing_m, number_of_bays=number_of_bays,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


def test_enumerate_bay_counts_tiles_the_length_within_range() -> None:
    # 30 m: n≥30/9=3.33→4 and n≤30/4.5=6.67→6 ⇒ 4,5,6 bays (7.5, 6.0, 5.0 m spacings).
    counts = enumerate_bay_counts(30.0)
    assert [n for n, _ in counts] == [4, 5, 6]
    for n, spacing in counts:
        assert abs(spacing - 30.0 / n) < 1e-9
        assert 4.5 - 1e-9 <= spacing <= 9.0 + 1e-9


def test_enumerate_returns_nothing_when_length_cannot_be_tiled() -> None:
    assert enumerate_bay_counts(4.0) == []  # shorter than one min-spacing bay
    assert enumerate_bay_counts(0.0) == []


def test_compare_generates_designs_and_ranks_by_total_primary_steel() -> None:
    cmp = compare_bay_layouts(_spec(bay_spacing_m=6.0, number_of_bays=5))
    assert isinstance(cmp, BayLayoutComparison)
    assert abs(cmp.building_length_m - 30.0) < 1e-9

    # The three sensible framings of a 30 m building are all present.
    assert {o.number_of_bays for o in cmp.options} == {4, 5, 6}

    for o in cmp.options:
        assert o.number_of_frames == o.number_of_bays + 1
        # Total primary steel is per-frame mass × number of frames (plain arithmetic on kernel output).
        if o.per_frame_mass_kg is not None:
            assert abs(o.total_primary_mass_kg - o.per_frame_mass_kg * o.number_of_frames) < 1e-6

    # Options are ranked lightest-first.
    masses = [o.total_primary_mass_kg for o in cmp.options if o.total_primary_mass_kg is not None]
    assert masses == sorted(masses)

    # The baseline is the input's own layout.
    assert cmp.baseline.number_of_bays == 5
    assert cmp.baseline.is_baseline

    # The lightest passing option really is passing and the minimum among passing options.
    assert cmp.lightest_passing is not None
    assert cmp.lightest_passing.passed
    passing = [o.total_primary_mass_kg for o in cmp.options if o.passed]
    assert cmp.lightest_passing.total_primary_mass_kg == min(passing)


def test_baseline_is_kept_even_when_its_spacing_is_outside_the_offered_range() -> None:
    # 3 bays × 10 m = 30 m; 10 m spacing is above the 9 m practice ceiling, but it's what the
    # engineer specified, so it must still appear as the baseline.
    cmp = compare_bay_layouts(_spec(bay_spacing_m=10.0, number_of_bays=3))
    assert cmp.baseline.number_of_bays == 3
    assert any(o.number_of_bays == 3 for o in cmp.options)
    # …alongside the in-range alternatives.
    assert {o.number_of_bays for o in cmp.options} >= {3, 4, 5, 6}


def test_is_deterministic() -> None:
    a = compare_bay_layouts(_spec())
    b = compare_bay_layouts(_spec())
    assert [o.total_primary_mass_kg for o in a.options] == [
        o.total_primary_mass_kg for o in b.options
    ]


# --- Span-split (width) comparison — the clear-span vs multi-span topology choice ---

def _wide_spec(number_of_spans: int = 1, span_m: float = 24.0) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=span_m, eaves_height_m=6.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=4, number_of_spans=number_of_spans,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        restraints=Restraints(rafter_restraint_spacing_m=1.5, column_restraint_spacing_m=2.0),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


def test_enumerate_span_counts_splits_width() -> None:
    # 24 m: n≥24/40→1 and n≤24/8→3 ⇒ 1×24, 2×12, 3×8.
    counts = enumerate_span_counts(24.0)
    assert [n for n, _ in counts] == [1, 2, 3]
    for n, w in counts:
        assert abs(w - 24.0 / n) < 1e-9


def test_compare_span_splits_offers_clear_span_and_multispan() -> None:
    cmp = compare_span_splits(_wide_spec(number_of_spans=1, span_m=24.0))
    assert abs(cmp.building_width_m - 24.0) < 1e-9
    assert {o.number_of_spans for o in cmp.options} == {1, 2, 3}
    assert cmp.baseline.number_of_spans == 1

    # Multi-span options are flagged PROVISIONAL; the single clear span is not.
    for o in cmp.options:
        assert o.provisional == (o.number_of_spans > 1)
    # Ranked lightest-first.
    masses = [o.total_primary_mass_kg for o in cmp.options if o.total_primary_mass_kg is not None]
    assert masses == sorted(masses)
    assert cmp.lightest_passing is not None


def test_compare_span_splits_is_deterministic() -> None:
    a = compare_span_splits(_wide_spec(1, 24.0))
    b = compare_span_splits(_wide_spec(1, 24.0))
    assert [o.total_primary_mass_kg for o in a.options] == [
        o.total_primary_mass_kg for o in b.options
    ]
