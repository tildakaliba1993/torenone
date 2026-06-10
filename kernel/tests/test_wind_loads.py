"""Tests for wind frame-load assembly — SANS 10160-3:2019 (Task 1.6d, PRD FR-7).

Checks the peak velocity pressure against a hand calc, the net = qp·(cpe−cpi) relationship, the
explicit uplift case (negative rafter UDLs), and that a windward dominant opening increases uplift.
"""

from __future__ import annotations

import math

import pytest

from torenone_kernel.loads.wind_loads import wind_loads
from torenone_kernel.models import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    TerrainCategory,
    WindContext,
)


def _spec(has_dominant_opening: bool = False) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=24.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0, number_of_bays=7
        ),
        dead=DeadLoadInputs(roof_kpa=0.15),
        wind=WindContext(
            basic_wind_speed_ms=40.0,
            terrain_category=TerrainCategory.B,
            site_altitude_m=0.0,
            has_dominant_opening=has_dominant_opening,
        ),
    )


def test_reference_height_is_apex_and_qp_matches_hand_calc() -> None:
    r = wind_loads(_spec())
    ze = 6.0 + 12.0 * math.tan(math.radians(10.0))  # apex = 8.116 m
    assert r.reference_height_m == pytest.approx(ze)
    # cr(ze,B)=1.36·(ze/300)^0.095; vp=cr·40; qp=½·1.20·vp²/1000 ≈ 0.894 kPa
    cr = 1.36 * (ze / 300.0) ** 0.095
    vp = cr * 40.0
    assert r.peak_velocity_pressure_kpa == pytest.approx(0.5 * 1.20 * vp**2 / 1000.0, rel=1e-6)


def test_enclosed_has_four_cases() -> None:
    # enclosed cpi (+0.2, −0.3) × roof branches (suction, pressure)
    assert len(wind_loads(_spec()).cases) == 4
    assert "enclosed" in wind_loads(_spec()).scenario


def test_net_cp_and_udl_are_consistent() -> None:
    r = wind_loads(_spec())
    qp, trib = r.peak_velocity_pressure_kpa, 6.0
    for c in r.cases:
        assert c.windward_column_udl_kn_per_m == pytest.approx(qp * c.net_cp_windward_wall * trib)
        assert c.windward_rafter_udl_kn_per_m == pytest.approx(qp * c.net_cp_windward_roof * trib)


def test_uplift_case_has_negative_rafter_loads() -> None:
    r = wind_loads(_spec())
    # The cpi=+0.2 + roof-suction case maximises uplift: both rafter UDLs act upward (negative).
    uplift = min(r.cases, key=lambda c: c.windward_rafter_udl_kn_per_m)
    assert uplift.windward_rafter_udl_kn_per_m < 0
    assert uplift.leeward_rafter_udl_kn_per_m < 0


def test_windward_dominant_opening_increases_uplift() -> None:
    enclosed_uplift = min(c.windward_rafter_udl_kn_per_m for c in wind_loads(_spec()).cases)
    dominant_uplift = min(
        c.windward_rafter_udl_kn_per_m for c in wind_loads(_spec(has_dominant_opening=True)).cases
    )
    assert dominant_uplift < enclosed_uplift  # more negative = larger uplift
    assert "dominant opening" in wind_loads(_spec(has_dominant_opening=True)).scenario
