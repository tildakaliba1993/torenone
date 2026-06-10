"""Tests for imposed roof load per SANS 10160-2 (Task 1.5, PRD FR-6).

The code value (0.4 kN/m² for an inaccessible roof, SANS 10160-2 Table 5) is PROVISIONAL pending
registered-engineer sign-off. These tests pin the sourced value and the line-load derivation, and
assert that out-of-scope accessible roofs fail loudly rather than guessing.
"""

from __future__ import annotations

import pytest

from torenone_kernel.loads import INACCESSIBLE_ROOF_QK_KPA, imposed_roof_loads
from torenone_kernel.models import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    TerrainCategory,
    WindContext,
)


def _spec(roof_access: bool = False, bay_spacing_m: float = 6.0) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=24.0,
            eaves_height_m=6.0,
            roof_pitch_deg=10.0,
            bay_spacing_m=bay_spacing_m,
            number_of_bays=7,
        ),
        dead=DeadLoadInputs(roof_kpa=0.15),
        imposed=ImposedLoadInputs(roof_access=roof_access),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
    )


def test_inaccessible_roof_value_is_the_sourced_sans_value() -> None:
    assert INACCESSIBLE_ROOF_QK_KPA == pytest.approx(0.4)  # SANS 10160-2 Table 5


def test_imposed_udl_matches_hand_calc() -> None:
    r = imposed_roof_loads(_spec(bay_spacing_m=6.0))
    assert r.roof_imposed_kpa == pytest.approx(0.4)
    assert r.tributary_width_m == pytest.approx(6.0)
    assert r.roof_udl_kn_per_m == pytest.approx(0.4 * 6.0)  # 2.4 kN/m
    assert r.clause == "SANS 10160-2:2011 Table 5"
    assert "naccessible" in r.category


def test_udl_scales_with_bay_spacing() -> None:
    assert imposed_roof_loads(_spec(bay_spacing_m=7.5)).roof_udl_kn_per_m == pytest.approx(0.4 * 7.5)


def test_accessible_roof_is_out_of_scope_and_raises() -> None:
    with pytest.raises(NotImplementedError):
        imposed_roof_loads(_spec(roof_access=True))
