"""Tests for external wall pressure coefficients — SANS 10160-3:2019 Table 6 (Task 1.6b).

The three tabulated h/d rows are asserted exactly against the standard; intermediate values check
the interpolation and the lack-of-correlation factor (cl. 8.3.2.4).
"""

from __future__ import annotations

import pytest

from torenone_kernel.loads.wind_pressure import (
    duopitch_roof_pressure_coefficients,
    wall_pressure_coefficients,
)


@pytest.mark.parametrize(
    "h_over_d,cpe_d,cpe_e",
    [
        (5.0, 0.8, -0.7),   # Table 6 row h/d = 5
        (1.0, 0.8, -0.5),   # Table 6 row h/d = 1
        (0.25, 0.7, -0.3),  # Table 6 row h/d ≤ 0.25
    ],
)
def test_wall_cpe_matches_table_6(h_over_d: float, cpe_d: float, cpe_e: float) -> None:
    w = wall_pressure_coefficients(h_over_d)
    assert w.cpe_windward == pytest.approx(cpe_d)
    assert w.cpe_leeward == pytest.approx(cpe_e)


def test_wall_cpe_clamps_below_and_above_table_range() -> None:
    assert wall_pressure_coefficients(0.1).cpe_windward == pytest.approx(0.7)  # ≤ 0.25 row
    assert wall_pressure_coefficients(10.0).cpe_leeward == pytest.approx(-0.7)  # ≥ 5 row


def test_wall_cpe_interpolates_leeward() -> None:
    # h/d = 3, between rows 1 (−0.5) and 5 (−0.7): −0.5 + (−0.2)·(3−1)/4 = −0.6
    assert wall_pressure_coefficients(3.0).cpe_leeward == pytest.approx(-0.6)


def test_lack_of_correlation_factor() -> None:
    # cl. 8.3.2.4: 0.85 for h/d ≤ 1, 1.0 for h/d ≥ 5, linear between.
    assert wall_pressure_coefficients(0.5).lack_of_correlation_factor == pytest.approx(0.85)
    assert wall_pressure_coefficients(5.0).lack_of_correlation_factor == pytest.approx(1.0)
    assert wall_pressure_coefficients(3.0).lack_of_correlation_factor == pytest.approx(0.925)


def test_carries_clause_citation() -> None:
    assert "Table 6" in wall_pressure_coefficients(1.0).clause


# --- Duopitch roof (SANS 10160-3:2019 Table 10, θ = 0°, zones H & I) ---


@pytest.mark.parametrize(
    "pitch,h_suction,h_pressure,i_suction",
    [
        (5.0, -0.6, 0.0, -0.6),   # Table 10 row α = 5°
        (15.0, -0.3, 0.2, -0.4),  # row α = 15°
        (30.0, -0.2, 0.4, -0.4),  # row α = 30°
        (45.0, -0.0, 0.6, -0.2),  # row α = 45°
    ],
)
def test_duopitch_roof_cpe_matches_table_10(
    pitch: float, h_suction: float, h_pressure: float, i_suction: float
) -> None:
    r = duopitch_roof_pressure_coefficients(pitch)
    assert r.windward_cpe_suction == pytest.approx(h_suction)
    assert r.windward_cpe_pressure == pytest.approx(h_pressure)
    assert r.leeward_cpe_suction == pytest.approx(i_suction)


def test_duopitch_roof_interpolates_within_pitch() -> None:
    # 10°, between 5° and 15°: H_suction −0.45, H_pressure +0.1, I_suction −0.5.
    r = duopitch_roof_pressure_coefficients(10.0)
    assert r.windward_cpe_suction == pytest.approx(-0.45)
    assert r.windward_cpe_pressure == pytest.approx(0.1)
    assert r.leeward_cpe_suction == pytest.approx(-0.5)


def test_duopitch_roof_windward_has_both_uplift_and_downforce() -> None:
    r = duopitch_roof_pressure_coefficients(10.0)
    assert r.windward_cpe_suction < 0 < r.windward_cpe_pressure  # uplift case AND downforce case


@pytest.mark.parametrize("pitch", [4.9, 0.5, 45.1, 60.0])
def test_duopitch_roof_out_of_scope_raises(pitch: float) -> None:
    with pytest.raises(NotImplementedError):
        duopitch_roof_pressure_coefficients(pitch)
