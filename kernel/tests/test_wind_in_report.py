"""design()/check() carry the SANS 10160-3 wind actions, and the report prints them.

These were computed by the wind chain but never surfaced — the orchestrator skipped
them and the renderer never printed the characteristic pressures (Part A fix).
"""

from __future__ import annotations

from torenone_kernel.design import check, design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import SectionChoice
from torenone_kernel.report.renderer import render_html


def _spec() -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=20, eaves_height_m=6, roof_pitch_deg=10, bay_spacing_m=6, number_of_bays=5
        ),
        dead=DeadLoadInputs(roof_kpa=0.15),
        wind=WindContext(basic_wind_speed_ms=36, terrain_category=TerrainCategory.B),
    )


class TestWindInResult:
    def test_design_carries_wind_actions(self) -> None:
        wind = design(_spec()).wind
        assert wind is not None
        assert wind.peak_velocity_pressure_kpa > 0
        assert len(wind.cases) >= 1
        # net coefficients + member line loads are populated (non-trivial)
        case = wind.cases[0]
        assert case.windward_column_udl_kn_per_m != 0.0
        assert "10160-3" in wind.clause

    def test_check_mode_also_carries_wind(self) -> None:
        spec = _spec()
        sections = [
            SectionChoice(member=s.member, designation=s.designation)
            for s in design(spec).sections
        ]
        result = check(spec, sections)
        assert result.wind is not None
        assert result.wind.peak_velocity_pressure_kpa > 0

    def test_design_runs_the_wind_combinations(self) -> None:
        # Part B: members are now CHECKED under ULS-2/3 wind (results suffixed + counted).
        checks = design(_spec()).checks
        names = [c.name for c in checks]
        assert any("[ULS-2 wind]" in n for n in names)
        assert any("[ULS-3 wind]" in n for n in names)
        wind_checks = [c for c in checks if "wind]" in c.name]
        assert wind_checks and all(c.utilisation >= 0 for c in wind_checks)
        # the worst wind utilisation is folded into the governing utilisation / passed
        result = design(_spec())
        assert result.governing_utilisation >= max(c.utilisation for c in wind_checks)


class TestWindInReport:
    def test_report_prints_the_wind_pressures(self) -> None:
        result = design(_spec())
        html = render_html(result)
        assert "Characteristic Wind Actions" in html
        assert "Peak velocity pressure" in html
        # the actual qp value is rendered (3 dp, as in the template)
        assert f"{result.wind.peak_velocity_pressure_kpa:.3f}" in html
