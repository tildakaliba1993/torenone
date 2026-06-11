"""Contract tests for the FrameSpec domain model (Task 1.1, PRD FR-1/FR-3).

The spec must be: strongly typed, range-validated, immutable (frozen), and intolerant of
unknown fields — so a misparse from the AI layer fails loudly instead of silently feeding a
wrong design into the kernel. No engineering numbers are computed here beyond pure geometry.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError
from torenone_kernel.models import (
    BaseFixity,
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    SteelGrade,
    TerrainCategory,
    WindContext,
)


def _geometry(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "span_m": 24.0,
        "eaves_height_m": 6.0,
        "roof_pitch_deg": 10.0,
        "bay_spacing_m": 6.0,
        "number_of_bays": 7,
    }
    base.update(overrides)
    return base


def _reference_frame() -> FrameSpec:
    """A typical SA warehouse portal — the Reference Frame v1 shape (see REFERENCES doc)."""
    return FrameSpec(
        geometry=FrameGeometry(**_geometry()),
        dead=DeadLoadInputs(roof_kpa=0.15),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
    )


def test_reference_frame_constructs() -> None:
    spec = _reference_frame()
    assert spec.geometry.span_m == 24.0
    assert spec.base_fixity is BaseFixity.PINNED  # MVP default
    assert spec.materials.steel_grade is SteelGrade.S355JR  # default


def test_geometry_is_computed_not_invented() -> None:
    geo = FrameGeometry(**_geometry())
    expected_apex = 6.0 + (24.0 / 2.0) * math.tan(math.radians(10.0))
    assert geo.apex_height_m == pytest.approx(expected_apex)
    assert geo.building_length_m == pytest.approx(42.0)


def test_defaults_are_safe() -> None:
    spec = _reference_frame()
    # Unspecified restraints => None => kernel must treat as unrestrained (conservative).
    assert spec.restraints.rafter_restraint_spacing_m is None
    assert spec.restraints.column_restraint_spacing_m is None
    assert spec.imposed.roof_access is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("span_m", 0.0),
        ("span_m", -5.0),
        ("eaves_height_m", 0.0),
        ("roof_pitch_deg", 0.0),       # a portal must have a pitch
        ("roof_pitch_deg", 45.1),      # >45 is out of MVP scope
        ("bay_spacing_m", 0.0),
        ("number_of_bays", 0),
    ],
)
def test_invalid_geometry_is_rejected(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        FrameGeometry(**_geometry(**{field: value}))


def test_unknown_fields_are_rejected() -> None:
    # A hallucinated extra field from the AI layer must not slip through silently.
    with pytest.raises(ValidationError):
        FrameGeometry(**_geometry(), unexpected_field=1.0)


def test_spec_is_immutable() -> None:
    spec = _reference_frame()
    with pytest.raises(ValidationError):
        spec.base_fixity = BaseFixity.FIXED  # type: ignore[misc]


def test_restraint_spacing_must_be_positive_when_given() -> None:
    from torenone_kernel.models import Restraints

    Restraints(rafter_restraint_spacing_m=1.5)  # ok
    with pytest.raises(ValidationError):
        Restraints(rafter_restraint_spacing_m=0.0)


def test_wind_speed_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        WindContext(basic_wind_speed_ms=0.0, terrain_category=TerrainCategory.B)


def test_dead_load_components_non_negative() -> None:
    DeadLoadInputs(roof_kpa=0.0)  # ok
    with pytest.raises(ValidationError):
        DeadLoadInputs(roof_kpa=-0.1)


def test_materials_default_factory_is_independent() -> None:
    a = _reference_frame()
    b = _reference_frame()
    assert a.materials == b.materials
    assert a is not b
