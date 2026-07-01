"""Multi-span (internal-column) member design — Path B increment 3 (PROVISIONAL).

Builds on the validated multi-span statics (test_plane_frame_multispan.py): here we size the
rafters + external + internal (valley) columns on gravity, reusing the validated SANS check
pipeline, and confirm the result is well-formed and clearly marked PROVISIONAL. Wind + the last
mile are intentionally NOT modelled for multi-span yet.

Run: PYTHONPATH="kernel/src:tools" pytest kernel/tests/test_design_multispan.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.design import design
from torenone_kernel.models.enums import RoofType, TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    Restraints,
    WindContext,
)


def _multispan_spec(n_spans: int = 2, **geom_over: object) -> FrameSpec:
    geom = dict(
        span_m=18.0, eaves_height_m=6.0, roof_pitch_deg=8.0, bay_spacing_m=6.0,
        number_of_bays=4, number_of_spans=n_spans,
    )
    geom.update(geom_over)
    return FrameSpec(
        geometry=FrameGeometry(**geom),  # type: ignore[arg-type]
        dead=DeadLoadInputs(roof_kpa=0.20),
        restraints=Restraints(rafter_restraint_spacing_m=1.5, column_restraint_spacing_m=2.0),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


def test_designs_rafter_external_and_internal_columns() -> None:
    r = design(_multispan_spec(2))
    members = {s.member for s in r.sections}
    assert members == {"rafter", "column", "internal column"}
    assert r.passed
    assert r.total_steel_mass_kg and r.total_steel_mass_kg > 0


def test_marked_provisional_gravity_only() -> None:
    r = design(_multispan_spec(2))
    blob = " ".join(r.warnings).lower()
    assert "provisional" in blob and "multi-span" in blob
    assert "wind" in blob and "gravity" in blob
    # Last mile deferred, like mono-pitch.
    assert r.wind is None and r.baseplate is None and r.footing is None
    assert not r.connections


def test_internal_column_carries_more_axial() -> None:
    """The valley column takes two half-spans → ~2× the axial of an external column (but ~0 moment,
    since adjacent spans' moments cancel — so it can still be a lighter *section* than the
    moment-governed external column)."""
    from torenone_kernel.analysis.plane_frame import MultiSpanAnalysis
    from torenone_kernel.sections import SectionLibrary

    sec = SectionLibrary.load_default().get("356x171x51")
    d = MultiSpanAnalysis(_multispan_spec(2), sec, sec, sec).demand(10.0)
    assert d.int_col_cu_kn > d.ext_col_cu_kn
    assert d.int_col_cu_kn == pytest.approx(2.0 * d.ext_col_cu_kn, rel=0.25)


def test_more_spans_use_more_steel() -> None:
    m2 = design(_multispan_spec(2)).total_steel_mass_kg
    m3 = design(_multispan_spec(3)).total_steel_mass_kg
    assert m2 and m3 and m3 > m2


def test_is_deterministic() -> None:
    a = design(_multispan_spec(2))
    b = design(_multispan_spec(2))
    assert a.model_dump() == b.model_dump()


def test_multispan_monopitch_is_rejected() -> None:
    spec = _multispan_spec(2, roof_type=RoofType.MONOPITCH)
    with pytest.raises(ValueError, match="mono-pitch"):
        design(spec)


def test_single_span_uses_the_normal_path() -> None:
    """number_of_spans=1 (the default) still routes to the standard single-bay design."""
    r = design(_multispan_spec(1))
    members = {s.member for s in r.sections}
    assert members == {"rafter", "column"}  # no internal column
