"""Tests for imposed roof load per SANS 10160-2 (Task 1.5, PRD FR-6).

Values VERIFIED vs SANS 10160-2:2011 Table 5, category H2 (inaccessible roof, normal
maintenance & repair) — area-dependent: 0.50 kN/m² (A ≤ 3 m²) → 0.25 kN/m² (A ≥ 15 m²),
linearly interpolated. These tests pin the table values, the interpolation, the loaded-area
basis (bay × span/2) and the line-load derivation, and assert that out-of-scope accessible
roofs fail loudly rather than guessing.
"""

from __future__ import annotations

import pytest
from torenone_kernel.loads import imposed_roof_loads, inaccessible_roof_qk_kpa
from torenone_kernel.models import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    TerrainCategory,
    WindContext,
)


def _spec(
    roof_access: bool = False, bay_spacing_m: float = 6.0, span_m: float = 24.0
) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=span_m,
            eaves_height_m=6.0,
            roof_pitch_deg=10.0,
            bay_spacing_m=bay_spacing_m,
            number_of_bays=7,
        ),
        dead=DeadLoadInputs(roof_kpa=0.15),
        imposed=ImposedLoadInputs(roof_access=roof_access),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
    )


def test_qk_table_bounds_and_interpolation() -> None:
    # SANS 10160-2 Table 5 H2: 0.50 at A≤3, 0.25 at A≥15, interpolated between.
    assert inaccessible_roof_qk_kpa(2.0) == pytest.approx(0.50)
    assert inaccessible_roof_qk_kpa(3.0) == pytest.approx(0.50)
    assert inaccessible_roof_qk_kpa(15.0) == pytest.approx(0.25)
    assert inaccessible_roof_qk_kpa(45.0) == pytest.approx(0.25)
    # midpoint A=9: qk = 0.25 + (15-9)/48 = 0.375
    assert inaccessible_roof_qk_kpa(9.0) == pytest.approx(0.375)


def test_typical_frame_uses_large_area_value() -> None:
    # span 24, bay 6 -> loaded area = 6 × 12 = 72 m² ≥ 15 -> qk = 0.25 kN/m².
    r = imposed_roof_loads(_spec(bay_spacing_m=6.0, span_m=24.0))
    assert r.roof_imposed_kpa == pytest.approx(0.25)
    assert r.tributary_width_m == pytest.approx(6.0)
    assert r.roof_udl_kn_per_m == pytest.approx(0.25 * 6.0)  # 1.5 kN/m
    assert r.clause == "SANS 10160-2:2011 Table 5 (category H2)"
    assert "naccessible" in r.category


def test_small_frame_picks_up_interpolated_value() -> None:
    # span 4, bay 3 -> loaded area = 3 × 2 = 6 m² (3<A<15) -> qk = 0.25 + (15-6)/48 = 0.4375.
    r = imposed_roof_loads(_spec(bay_spacing_m=3.0, span_m=4.0))
    assert r.roof_imposed_kpa == pytest.approx(0.4375)
    assert r.roof_udl_kn_per_m == pytest.approx(0.4375 * 3.0)


def test_udl_scales_with_bay_spacing() -> None:
    # span 24, bay 7.5 -> area 90 m² -> qk = 0.25; UDL = 0.25 × 7.5.
    r = imposed_roof_loads(_spec(bay_spacing_m=7.5, span_m=24.0))
    assert r.roof_udl_kn_per_m == pytest.approx(0.25 * 7.5)


def test_accessible_roof_is_out_of_scope_and_raises() -> None:
    with pytest.raises(NotImplementedError):
        imposed_roof_loads(_spec(roof_access=True))
