"""Tests for SANS 10160-1 load combinations (Task 1.7, PRD FR-8).

Factors transcribed from the DRAFT SANS 10160-1:2009 (Table 3 + eq. 6/7/10) — PROVISIONAL pending
confirmation vs the final standard. These tests pin the factor values and the key SANS-specific
structure (inaccessible roof ⇒ imposed & wind never combine as accompanying actions; an explicit
favourable-permanent uplift combination).
"""

from __future__ import annotations

import pytest

from torenone_kernel.loads.combinations import load_combinations
from torenone_kernel.models import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    LimitState,
    TerrainCategory,
    WindContext,
)


def _spec(roof_access: bool = False) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=24.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0, number_of_bays=7
        ),
        dead=DeadLoadInputs(roof_kpa=0.15),
        imposed=ImposedLoadInputs(roof_access=roof_access),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
    )


def _by_factors(spec: FrameSpec) -> dict[str, dict[str, float]]:
    return {c.name: c.factors for c in load_combinations(spec)}


def test_uls_gravity_factors() -> None:
    combos = load_combinations(_spec())
    gravity = next(c for c in combos if c.name.startswith("ULS-1"))
    assert gravity.factors == {"dead": 1.2, "imposed": 1.6}
    assert gravity.limit_state is LimitState.ULS


def test_uls_wind_factors_and_uplift_uses_favourable_permanent() -> None:
    combos = {c.name[:5]: c for c in load_combinations(_spec())}
    assert combos["ULS-2"].factors == {"dead": 1.2, "wind": 1.3}
    assert combos["ULS-3"].factors == {"dead": 0.9, "wind": 1.3}  # uplift: favourable permanent


def test_str_p_dominant_permanent() -> None:
    combos = {c.name[:5]: c for c in load_combinations(_spec())}
    assert combos["ULS-4"].factors == {"dead": 1.35, "imposed": 1.0}


def test_sls_combinations() -> None:
    combos = {c.name[:5]: c for c in load_combinations(_spec())}
    assert combos["SLS-1"].factors == {"dead": 1.1, "imposed": 1.0}
    assert combos["SLS-1"].limit_state is LimitState.SLS
    assert combos["SLS-2"].factors == {"dead": 1.0, "wind": 1.0}


def test_imposed_and_wind_never_combine_for_inaccessible_roof() -> None:
    # ψ0 = 0 (Table 2): no combination contains BOTH imposed and wind.
    for c in load_combinations(_spec()):
        assert not ({"imposed", "wind"} <= set(c.factors))


def test_accessible_roof_out_of_scope() -> None:
    with pytest.raises(NotImplementedError):
        load_combinations(_spec(roof_access=True))
