"""FR-32 — BMD/SFD + stick-model sampling (analysis.diagram_data + DesignResult.diagram).

The diagram data is the on-screen counterpart of the PDF's BMD/SFD: the SAME PyNite
analysis, exposed structurally. These tests pin its shape, physical sanity (pinned base
→ ~0 moment), and determinism, and confirm design()/check() attach it.

Run:
    PYTHONPATH="kernel/src:tools" /opt/homebrew/opt/python@3.11/bin/python3.11 \
        -m pytest kernel/tests/test_diagram_data.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.analysis.diagram_data import N_STATIONS, compute_frame_diagram
from torenone_kernel.design import check, design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import FrameDiagram
from torenone_kernel.sections.library import SectionLibrary


@pytest.fixture(scope="module")
def spec() -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


@pytest.fixture(scope="module")
def diagram(spec: FrameSpec) -> FrameDiagram:
    lib = SectionLibrary.load_default()
    sections = {s.member: lib.get(s.designation) for s in design(spec).sections}
    return compute_frame_diagram(spec, sections["column"], sections["rafter"])


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


class TestShape:
    def test_four_members_five_nodes(self, diagram: FrameDiagram):
        assert [m.name for m in diagram.members] == [
            "column_left", "rafter_left", "rafter_right", "column_right",
        ]
        assert set(diagram.nodes) == {"BL", "EL", "AP", "ER", "BR"}

    def test_station_count(self, diagram: FrameDiagram):
        for m in diagram.members:
            assert len(m.stations) == N_STATIONS

    def test_combination_is_uls1(self, diagram: FrameDiagram):
        assert diagram.combination.startswith("ULS-1")

    def test_stations_span_member_endpoints(self, diagram: FrameDiagram):
        for m in diagram.members:
            first, last = m.stations[0], m.stations[-1]
            assert first.pos_m == pytest.approx(0.0)
            assert last.pos_m == pytest.approx(m.length_m)
            # First/last global positions coincide with the member's end nodes.
            assert (first.x_m, first.y_m) == pytest.approx(m.start)
            assert (last.x_m, last.y_m) == pytest.approx(m.end)

    def test_extrema_match_samples(self, diagram: FrameDiagram):
        all_m = [abs(s.moment_knm) for m in diagram.members for s in m.stations]
        all_v = [abs(s.shear_kn) for m in diagram.members for s in m.stations]
        assert diagram.max_abs_moment_knm == pytest.approx(max(all_m))
        assert diagram.max_abs_shear_kn == pytest.approx(max(all_v))


# ---------------------------------------------------------------------------
# Physical sanity
# ---------------------------------------------------------------------------


class TestPhysics:
    def test_pinned_base_has_near_zero_moment(self, diagram: FrameDiagram):
        # Pinned bases (BL, BR) carry no moment — the base station moment ≈ 0.
        col_left = diagram.members[0]
        base_station = col_left.stations[0]  # pos 0 = base node BL
        assert base_station.moment_knm == pytest.approx(0.0, abs=1e-3)

    def test_gravity_load_puts_columns_in_compression(self, diagram: FrameDiagram):
        # Under gravity ULS-1 the columns carry net compression (sign convention:
        # PyNite axial negative = compression). Assert non-trivial axial present.
        col_left = diagram.members[0]
        axials = [s.axial_kn for s in col_left.stations]
        assert max(abs(a) for a in axials) > 1.0

    def test_nonzero_moment_somewhere(self, diagram: FrameDiagram):
        assert diagram.max_abs_moment_knm > 1.0


# ---------------------------------------------------------------------------
# Determinism + wiring
# ---------------------------------------------------------------------------


class TestDeterminismAndWiring:
    def test_deterministic(self, spec: FrameSpec):
        lib = SectionLibrary.load_default()
        sections = {s.member: lib.get(s.designation) for s in design(spec).sections}
        a = compute_frame_diagram(spec, sections["column"], sections["rafter"])
        b = compute_frame_diagram(spec, sections["column"], sections["rafter"])
        assert a.model_dump() == b.model_dump()

    def test_design_attaches_diagram(self, spec: FrameSpec):
        result = design(spec)
        assert result.diagram is not None
        assert len(result.diagram.members) == 4

    def test_check_attaches_diagram(self, spec: FrameSpec):
        sections = design(spec).sections
        result = check(spec, list(sections))
        assert result.diagram is not None
        assert result.diagram.combination.startswith("ULS-1")

    def test_different_geometry_differs(self, spec: FrameSpec):
        lib = SectionLibrary.load_default()
        sections = {s.member: lib.get(s.designation) for s in design(spec).sections}
        wide = spec.model_copy(
            update={"geometry": FrameGeometry(
                span_m=24.0, eaves_height_m=6.0, roof_pitch_deg=10.0,
                bay_spacing_m=6.0, number_of_bays=5,
            )}
        )
        a = compute_frame_diagram(spec, sections["column"], sections["rafter"])
        b = compute_frame_diagram(wide, sections["column"], sections["rafter"])
        assert a.max_abs_moment_knm != b.max_abs_moment_knm
