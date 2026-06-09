"""Tests for the section-property model and library machinery (Task 1.2).

The section records here are SYNTHETIC and clearly non-physical ('TEST-*' designations, round
numbers). They exist ONLY to exercise the loader/lookup/ordering machinery. No real SAISC data
is asserted — that is supplied by the registered engineer and validated separately.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from torenone_kernel.sections import SectionLibrary, SectionProperties


def _record(designation: str, mass: float) -> dict[str, object]:
    """A complete but SYNTHETIC section record (not a real section)."""
    return {
        "designation": designation,
        "mass_per_metre_kg_m": mass,
        "area_mm2": 1000.0,
        "depth_mm": 400.0,
        "width_mm": 180.0,
        "web_thickness_mm": 9.0,
        "flange_thickness_mm": 14.0,
        "second_moment_ix_mm4": 2.3e8,
        "second_moment_iy_mm4": 1.3e7,
        "elastic_modulus_sx_mm3": 1.1e6,
        "plastic_modulus_zx_mm3": 1.3e6,
        "radius_gyration_rx_mm": 160.0,
        "radius_gyration_ry_mm": 40.0,
        "torsion_constant_j_mm4": 5.1e5,
        "warping_constant_cw_mm6": 4.9e11,
    }


def test_section_properties_reject_non_positive_values() -> None:
    SectionProperties(**_record("TEST-A", 50.0))  # ok
    with pytest.raises(ValidationError):
        SectionProperties(**{**_record("TEST-A", 50.0), "area_mm2": 0.0})


def test_library_lookup() -> None:
    lib = SectionLibrary.from_records([_record("TEST-A", 50.0), _record("TEST-B", 66.0)])
    assert len(lib) == 2
    assert "TEST-A" in lib
    assert lib.get("TEST-B").mass_per_metre_kg_m == 66.0


def test_library_unknown_section_raises_keyerror() -> None:
    lib = SectionLibrary.from_records([_record("TEST-A", 50.0)])
    with pytest.raises(KeyError):
        lib.get("DOES-NOT-EXIST")


def test_library_rejects_duplicate_designations() -> None:
    with pytest.raises(ValueError):
        SectionLibrary.from_records([_record("TEST-A", 50.0), _record("TEST-A", 60.0)])


def test_by_increasing_mass_orders_lightest_first() -> None:
    lib = SectionLibrary.from_records(
        [_record("HEAVY", 90.0), _record("LIGHT", 30.0), _record("MID", 55.0)]
    )
    order = [s.designation for s in lib.by_increasing_mass()]
    assert order == ["LIGHT", "MID", "HEAVY"]


def test_load_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "sections.json"
    path.write_text(json.dumps([_record("TEST-A", 50.0), _record("TEST-B", 66.0)]), encoding="utf-8")
    lib = SectionLibrary.load_json(path)
    assert set(lib.designations()) == {"TEST-A", "TEST-B"}


def test_load_json_rejects_non_array(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    with pytest.raises(ValueError):
        SectionLibrary.load_json(path)
