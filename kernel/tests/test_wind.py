"""Tests for the wind engine — SANS 10160-3:2019 (Task 1.6a, PRD FR-7).

The roughness factor cr(z) is validated against the standard's OWN Table 3 (cr vs height for each
terrain category) — i.e. our implementation reproduces the code's published table to within
rounding. Air density is checked against Table 4. Values are transcribed from the official
SANS 10160-3:2019 (still subject to the engineer's final sign-off — REFERENCES §5).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from torenone_kernel.loads.wind import (
    SA_BASIC_WIND_SPEED_ZONES_MS,
    TERRAIN_PARAMETERS,
    TerrainParameters,
    air_density,
    peak_velocity_pressure_kpa,
    peak_wind_speed,
    roughness_factor,
)
from torenone_kernel.models.enums import TerrainCategory

# SANS 10160-3:2019 Table 3 — Variation of cr(z) with height (the validation oracle).
_TABLE3_ELEVATIONS_M = [0, 2, 4, 6, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100]
_TABLE3 = {
    "A": [0.92, 0.97, 1.02, 1.05, 1.09, 1.12, 1.14, 1.17, 1.20, 1.22, 1.23, 1.24, 1.26, 1.27, 1.28],
    "B": [0.85, 0.85, 0.90, 0.94, 0.98, 1.02, 1.05, 1.09, 1.12, 1.15, 1.17, 1.18, 1.20, 1.21, 1.23],
    "C": [0.73, 0.73, 0.73, 0.77, 0.85, 0.91, 0.95, 1.00, 1.04, 1.07, 1.09, 1.12, 1.14, 1.15, 1.17],
    "D": [0.71, 0.71, 0.71, 0.71, 0.71, 0.78, 0.83, 0.90, 0.95, 0.98, 1.01, 1.04, 1.06, 1.08, 1.10],
}


@pytest.mark.parametrize("cat", ["A", "B", "C", "D"])
def test_roughness_factor_reproduces_sans_table_3(cat: str) -> None:
    category = TerrainCategory[cat]
    for z, ref in zip(_TABLE3_ELEVATIONS_M, _TABLE3[cat], strict=True):
        cr = roughness_factor(float(z), category)
        # Table 3 is rounded to 2 d.p.; our value must match within that rounding.
        assert cr == pytest.approx(ref, abs=0.011), f"{cat} @ {z} m: {cr:.3f} vs table {ref}"


def test_table1_parameters_are_the_sans_values() -> None:
    assert TERRAIN_PARAMETERS[TerrainCategory.B] == TerrainParameters(
        zg_m=300, zo_m=0, zc_m=2, alpha=0.095
    )
    assert TERRAIN_PARAMETERS[TerrainCategory.C].zo_m == 3.0  # reference plane matters for C/D


def test_air_density_table4_points_and_interpolation() -> None:
    assert air_density(0) == pytest.approx(1.20)
    assert air_density(1000) == pytest.approx(1.06)
    assert air_density(2000) == pytest.approx(0.94)
    assert air_density(750) == pytest.approx(1.09)  # interp between 500 (1.12) and 1000 (1.06)
    assert air_density(5000) == pytest.approx(0.94)  # clamped beyond table range


def test_peak_wind_speed_uses_cr_and_unit_peak_factor() -> None:
    vp = peak_wind_speed(10.0, TerrainCategory.B, basic_wind_speed_ms=40.0)
    assert vp == pytest.approx(roughness_factor(10.0, TerrainCategory.B) * 40.0)  # vb,peak = 1.0·vb


def test_peak_velocity_pressure() -> None:
    # qp = ½·ρ·vp² ; vp=40 m/s, ρ=1.20 kg/m³ (sea level) -> 960 Pa = 0.96 kPa.
    assert peak_velocity_pressure_kpa(40.0, 1.20) == pytest.approx(0.96)


def test_sa_basic_wind_speed_zones() -> None:
    assert SA_BASIC_WIND_SPEED_ZONES_MS == (32.0, 36.0, 40.0, 44.0)


def test_terrain_parameters_validate_positive() -> None:
    TerrainParameters(zg_m=300, zo_m=0, zc_m=2, alpha=0.095)  # ok (zo may be 0)
    with pytest.raises(ValidationError):
        TerrainParameters(zg_m=0, zo_m=0, zc_m=2, alpha=0.095)
