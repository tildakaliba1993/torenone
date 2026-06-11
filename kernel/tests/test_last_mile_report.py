"""Task 2.8 — last-mile report sections (connections, baseplate, footing, tonnage).

Renders a complete design() result and asserts the dedicated report sections appear,
clause-referenced with pass/fail + utilisation (PRD FR-18/25/28/29/30).

Run:
    PYTHONPATH="kernel/src:tools" /opt/homebrew/opt/python@3.11/bin/python3.11 \
        -m pytest kernel/tests/test_last_mile_report.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FoundationInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.report.renderer import render_html


def _spec(allowable_bearing_kpa: float | None = None) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        foundation=FoundationInputs(allowable_bearing_kpa=allowable_bearing_kpa),
    )


@pytest.fixture(scope="module")
def html_with_footing() -> str:
    return render_html(design(_spec(allowable_bearing_kpa=150.0)))


@pytest.fixture(scope="module")
def html_no_footing() -> str:
    return render_html(design(_spec()))


# ---------------------------------------------------------------------------
# Connection / baseplate / footing sections
# ---------------------------------------------------------------------------


class TestSections:
    def test_connection_section(self, html_with_footing):
        assert "Connection Design" in html_with_footing
        assert "Eaves connection" in html_with_footing
        assert "Apex connection" in html_with_footing

    def test_connection_checks_rendered(self, html_with_footing):
        assert "connection: bolt tension" in html_with_footing
        assert "connection: flange weld" in html_with_footing

    def test_baseplate_section(self, html_with_footing):
        assert "Column Baseplate" in html_with_footing
        assert "baseplate: concrete bearing" in html_with_footing
        assert "baseplate: anchor shear" in html_with_footing

    def test_footing_section_with_clause(self, html_with_footing):
        assert "Pad Footing" in html_with_footing
        assert "footing: soil bearing" in html_with_footing
        assert "SANS 10100-1" in html_with_footing

    def test_footing_omitted_note_when_no_bearing(self, html_no_footing):
        assert "Pad footing not designed" in html_no_footing
        assert "footing: soil bearing" not in html_no_footing


# ---------------------------------------------------------------------------
# Tonnage + cost (FR-25)
# ---------------------------------------------------------------------------


class TestTonnage:
    def test_tonnage_rendered(self, html_with_footing):
        result = design(_spec(allowable_bearing_kpa=150.0))
        assert "Total steel tonnage" in html_with_footing
        assert f"{result.total_steel_tonnes:.3f}" in html_with_footing

    def test_cost_still_present(self, html_with_footing):
        assert "Indicative fabricated steel cost" in html_with_footing


# ---------------------------------------------------------------------------
# Detail checks excluded from the member table (no duplication)
# ---------------------------------------------------------------------------


class TestNoDuplication:
    def test_member_checks_table_excludes_details(self, html_with_footing):
        # The member code-checks heading is present...
        assert "Member Code Checks" in html_with_footing
        # ...and the detail checks live only in their own sections (rendered once each).
        assert html_with_footing.count("baseplate: concrete bearing") == 1
        assert html_with_footing.count("footing: punching shear (1.5d)") == 1
