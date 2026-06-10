"""Tests for the wind engine (Task 1.6a, PRD FR-7).

The velocity/pressure FORMULAS are public/Eurocode-aligned and are verified here by hand with
explicit inputs. The SANS-specific terrain table is PENDING (SOURCES.md E7), so the terrain lookup
must RAISE — proving the kernel never fabricates those values.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from torenone_kernel.loads.wind import (
    SA_BASIC_WIND_SPEED_ZONES_MS,
    TerrainParameters,
    kr_from_z0,
    peak_velocity_pressure_kpa,
    peak_wind_speed,
    roughness_factor,
    sans_terrain_parameters,
)
from torenone_kernel.models.enums import TerrainCategory


def test_kr_reference_terrain() -> None:
    # kr = 0.19·(z0/0.05)^0.07 — at the reference z0 = 0.05 m, kr = 0.19.
    assert kr_from_z0(0.05) == pytest.approx(0.19)
    assert kr_from_z0(0.30) > kr_from_z0(0.05)  # rougher terrain -> larger kr


def test_roughness_factor_formula() -> None:
    cr = roughness_factor(10.0, z0_m=0.05, zmin_m=2.0, kr=0.19)
    assert cr == pytest.approx(0.19 * math.log(10.0 / 0.05))
    # Reference terrain B at 10 m should give cr ≈ 1.0 (consistent with vb,0 defined there).
    assert cr == pytest.approx(1.0, abs=0.02)


def test_roughness_factor_clamps_below_zmin() -> None:
    below = roughness_factor(1.0, z0_m=0.05, zmin_m=2.0, kr=0.19)
    at_min = roughness_factor(2.0, z0_m=0.05, zmin_m=2.0, kr=0.19)
    assert below == pytest.approx(at_min)


def test_peak_wind_speed_uses_default_kr() -> None:
    vp = peak_wind_speed(10.0, z0_m=0.05, zmin_m=2.0, vb_peak_ms=40.0, co=1.0)
    assert vp == pytest.approx(roughness_factor(10.0, z0_m=0.05, zmin_m=2.0, kr=0.19) * 40.0)


def test_peak_velocity_pressure() -> None:
    # qp = ½·ρ·vp² ; vp=40 m/s, ρ=1.25 kg/m³ -> 1000 Pa = 1.0 kPa.
    assert peak_velocity_pressure_kpa(40.0, 1.25) == pytest.approx(1.0)


def test_sa_basic_wind_speed_zones_are_sourced_values() -> None:
    assert SA_BASIC_WIND_SPEED_ZONES_MS == (32.0, 36.0, 40.0, 44.0)


def test_sans_terrain_parameters_are_pending_and_raise() -> None:
    # SOURCES.md E7: SANS terrain table not in any free source — must not be fabricated.
    for category in TerrainCategory:
        with pytest.raises(NotImplementedError):
            sans_terrain_parameters(category)


def test_terrain_parameters_validate_positive() -> None:
    TerrainParameters(z0_m=0.05, zmin_m=2.0)  # ok once real values are supplied
    with pytest.raises(ValidationError):
        TerrainParameters(z0_m=0.0, zmin_m=2.0)
