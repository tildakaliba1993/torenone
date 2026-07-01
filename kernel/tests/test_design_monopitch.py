"""Mono-pitch (single-slope) member design — T1-3 increment 2 (PROVISIONAL).

Builds on the validated mono-pitch statics (test_plane_frame_monopitch.py): here we size the
single rafter + two columns on gravity, reusing the validated SANS check pipeline, and confirm
the result is well-formed and clearly marked PROVISIONAL. Wind + the last mile are intentionally
NOT modelled for mono-pitch yet.

Run: PYTHONPATH="kernel/src:tools" pytest kernel/tests/test_design_monopitch.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.design import check, design
from torenone_kernel.models.enums import RoofType, TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    Restraints,
    WindContext,
)
from torenone_kernel.models.results import SectionChoice
from torenone_kernel.report.renderer import render_html


def _monopitch_spec(**geom_over: object) -> FrameSpec:
    geom = dict(
        span_m=18.0, eaves_height_m=4.0, roof_pitch_deg=8.0, bay_spacing_m=6.0,
        number_of_bays=4, roof_type=RoofType.MONOPITCH,
    )
    geom.update(geom_over)
    return FrameSpec(
        geometry=FrameGeometry(**geom),  # type: ignore[arg-type]
        dead=DeadLoadInputs(roof_kpa=0.20),
        # Real sheds have purlins/girts; a single long rafter needs lateral restraint.
        restraints=Restraints(rafter_restraint_spacing_m=1.5, column_restraint_spacing_m=2.0),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


def test_high_eaves_geometry() -> None:
    g = FrameGeometry(
        span_m=18.0, eaves_height_m=4.0, roof_pitch_deg=8.0, bay_spacing_m=6.0,
        number_of_bays=4, roof_type=RoofType.MONOPITCH,
    )
    # High eaves rises over the FULL span (not half): 4 + 18*tan(8°).
    assert g.high_eaves_height_m == pytest.approx(6.53, abs=0.02)


def test_monopitch_designs_and_passes() -> None:
    result = design(_monopitch_spec())
    assert result.passed
    assert 0.0 < result.governing_utilisation <= 1.0
    members = {s.member for s in result.sections}
    assert members == {"rafter", "column"}


def test_monopitch_reuses_full_member_check_set() -> None:
    result = design(_monopitch_spec())
    names = [c.name for c in result.checks]
    # Rafter + column each get the validated axial/shear/moment/interaction checks, + deflection.
    for member in ("rafter", "column"):
        assert any(f"{member}: axial" in n for n in names)
        assert any(f"{member}: shear" in n for n in names)
        assert any(f"{member}: moment" in n for n in names)
        assert any(f"{member}: beam-column interaction" in n for n in names)
    assert any("deflection" in n.lower() for n in names)
    # Every check must cite a clause (safety contract).
    assert all(c.clause for c in result.checks)


def test_monopitch_is_flagged_provisional_with_last_mile_but_no_wind() -> None:
    # v2: the last mile (both eaves-knee connections + a baseplate) is now designed; wind still isn't.
    result = design(_monopitch_spec())
    blob = " ".join(result.warnings).lower()
    assert "mono-pitch" in blob and "provisional" in blob
    assert "wind" in blob and "not modelled" in blob  # wind still not modelled
    assert result.wind is None
    assert result.diagram is None
    # The last mile IS designed now — two eaves-knee connections + a (worst-base) baseplate.
    assert len(result.connections) == 2
    locations = {c.location for c in result.connections}
    assert locations == {"eaves (low)", "eaves (high)"}
    assert result.baseplate is not None
    # No footing without an allowable bearing pressure (never assumed).
    assert result.footing is None
    assert any("pad footing not designed" in w.lower() for w in result.warnings)


def test_monopitch_is_deterministic() -> None:
    a = design(_monopitch_spec())
    b = design(_monopitch_spec())
    assert [s.designation for s in a.sections] == [s.designation for s in b.sections]
    assert a.governing_utilisation == pytest.approx(b.governing_utilisation, rel=1e-12)


def test_monopitch_report_is_safe() -> None:
    """The calc-package report skips the duopitch-derived working/diagrams for mono-pitch and
    shows the high-eaves geometry + a clear note (never a misleading duopitch derivation)."""
    html = render_html(design(_monopitch_spec()))
    assert "High eaves height" in html            # mono-pitch geometry
    assert "Apex height</td>" not in html         # no duopitch apex row
    assert "not yet available for mono-pitch" in html  # working section noted, not re-derived
    assert "FR-26 provenance" not in html         # the duopitch show-your-working is skipped
    # The validated member checks (with clauses) are still present.
    assert "SANS 10162" in html


def test_check_mode_rejects_monopitch() -> None:
    with pytest.raises(ValueError, match="mono-pitch"):
        check(
            _monopitch_spec(),
            [SectionChoice(member="rafter", designation="IPE 400"),
             SectionChoice(member="column", designation="IPE 400")],
        )


def test_duopitch_default_is_unchanged() -> None:
    # Omitting roof_type ⇒ DUOPITCH ⇒ the existing (validated) path, still with wind + diagram.
    spec = FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0, bay_spacing_m=6.0, number_of_bays=5
        ),
        dead=DeadLoadInputs(roof_kpa=0.20),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )
    assert spec.geometry.roof_type == RoofType.DUOPITCH
    result = design(spec)
    assert result.passed
    assert result.wind is not None      # duopitch still models wind
    assert result.diagram is not None   # and diagrams
