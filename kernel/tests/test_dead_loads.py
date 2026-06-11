"""Tests for characteristic dead-load computation (Task 1.4, PRD FR-5).

Dead load is code-agnostic physics (self-weight + permanent area loads × tributary width), so
every expected value here is an explicit hand calculation. Self-weight uses g = 9.81 m/s².
"""

from __future__ import annotations

import pytest
from torenone_kernel.loads import GRAVITY_M_S2, dead_loads
from torenone_kernel.models import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    TerrainCategory,
    WindContext,
)
from torenone_kernel.sections import SectionLibrary


@pytest.fixture(scope="module")
def lib() -> SectionLibrary:
    return SectionLibrary.load_default()


def _spec(**dead_over: float) -> FrameSpec:
    dead = {"roof_kpa": 0.15, "services_kpa": 0.05, "wall_cladding_kpa": 0.10}
    dead.update(dead_over)
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=24.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0, number_of_bays=7
        ),
        dead=DeadLoadInputs(**dead),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
    )


def test_gravity_constant() -> None:
    assert GRAVITY_M_S2 == pytest.approx(9.81)


def test_dead_loads_match_hand_calc(lib: SectionLibrary) -> None:
    rafter = lib.get("IPE 200")  # 22.4 kg/m
    column = lib.get("152x152x23")  # 23.3 kg/m
    d = dead_loads(_spec(), rafter, column)

    # self-weight = mass(kg/m) × 9.81 / 1000  -> kN/m
    rafter_sw = 22.4 * 9.81 / 1000
    column_sw = 23.3 * 9.81 / 1000
    assert d.rafter_self_weight_kn_per_m == pytest.approx(rafter_sw)
    assert d.column_self_weight_kn_per_m == pytest.approx(column_sw)

    # roof area load = roof + services = 0.20 kPa; tributary = bay spacing = 6 m
    assert d.roof_area_load_kpa == pytest.approx(0.20)
    assert d.tributary_width_m == pytest.approx(6.0)

    # rafter UDL = 0.20 × 6 + self-weight = 1.2 + 0.219744
    assert d.rafter_udl_kn_per_m == pytest.approx(0.20 * 6.0 + rafter_sw)
    # wall cladding UDL on column = 0.10 × 6 = 0.6
    assert d.wall_cladding_udl_kn_per_m == pytest.approx(0.60)


def test_services_are_included_in_roof_area_load(lib: SectionLibrary) -> None:
    no_services = dead_loads(_spec(services_kpa=0.0), lib.get("IPE 200"), lib.get("152x152x23"))
    with_services = dead_loads(_spec(services_kpa=0.05), lib.get("IPE 200"), lib.get("152x152x23"))
    assert with_services.roof_area_load_kpa > no_services.roof_area_load_kpa


def test_heavier_roof_increases_rafter_udl(lib: SectionLibrary) -> None:
    light = dead_loads(_spec(roof_kpa=0.10), lib.get("IPE 200"), lib.get("152x152x23"))
    heavy = dead_loads(_spec(roof_kpa=0.30), lib.get("IPE 200"), lib.get("152x152x23"))
    assert heavy.rafter_udl_kn_per_m > light.rafter_udl_kn_per_m


def test_no_cladding_gives_zero_cladding_load(lib: SectionLibrary) -> None:
    d = dead_loads(_spec(wall_cladding_kpa=0.0), lib.get("IPE 200"), lib.get("152x152x23"))
    assert d.wall_cladding_udl_kn_per_m == 0.0
