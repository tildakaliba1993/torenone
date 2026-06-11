"""Spot-check tests for the packaged SAISC section dataset (Task 1.2).

These assert that the parsed/converted data matches INDEPENDENTLY-KNOWN published section
properties (standard IPE profiles; UK/SA universal columns). If the PDF parse, the unit
conversion, or the SAISC->schema notation mapping (Z=elastic, Zpl=plastic) were wrong, these
fail loudly.

⚠️ The dataset is PROVISIONAL pending a registered engineer's spot-check sign-off vs the SAISC
Red Book before the Phase 8 validation gate. These tests guard the machinery + a sample; they
are not a substitute for that sign-off.
"""

from __future__ import annotations

import pytest
from torenone_kernel.sections import SectionLibrary

REL = 0.01  # published values are exact to ~3 s.f.; 1% catches any parse/units error


@pytest.fixture(scope="module")
def lib() -> SectionLibrary:
    return SectionLibrary.load_default()


def test_dataset_loads_expected_count(lib: SectionLibrary) -> None:
    # IPE-AA/IPE (100–200) + UB + UC, no Class-4 sections.
    assert len(lib) == 64


@pytest.mark.parametrize(
    "designation,area_mm2,ix_mm4,sx_mm3,ry_mm",
    [
        # IPE (European standard — identical worldwide)
        ("IPE 100", 1030, 1.71e6, 34.2e3, 12.4),
        ("IPE 200", 2850, 19.4e6, 194e3, 22.4),
        # Universal Columns (UK/SA)
        ("203x203x46", 5880, 45.6e6, 449e3, 51.2),
        ("254x254x73", 9290, 114e6, 896e3, 64.6),
    ],
)
def test_section_matches_known_published_values(
    lib: SectionLibrary,
    designation: str,
    area_mm2: float,
    ix_mm4: float,
    sx_mm3: float,
    ry_mm: float,
) -> None:
    s = lib.get(designation)
    assert s.area_mm2 == pytest.approx(area_mm2, rel=REL)
    assert s.second_moment_ix_mm4 == pytest.approx(ix_mm4, rel=REL)
    assert s.elastic_modulus_sx_mm3 == pytest.approx(sx_mm3, rel=REL)  # SAISC 'Z'
    assert s.radius_gyration_ry_mm == pytest.approx(ry_mm, rel=REL)


def test_plastic_modulus_mapping_is_correct(lib: SectionLibrary) -> None:
    # IPE 100: Wpl,x = 39.4 cm^3 = 39.4e3 mm^3 (SAISC 'Zpl'), distinct from Wel = 34.2e3.
    s = lib.get("IPE 100")
    assert s.plastic_modulus_zx_mm3 == pytest.approx(39.4e3, rel=REL)
    assert s.plastic_modulus_zx_mm3 > s.elastic_modulus_sx_mm3  # plastic > elastic, always


def test_torsion_and_warping_present_and_positive(lib: SectionLibrary) -> None:
    s = lib.get("254x254x73")
    assert s.torsion_constant_j_mm4 > 0
    assert s.warping_constant_cw_mm6 > 0


def test_lightest_first_ordering(lib: SectionLibrary) -> None:
    ordered = lib.by_increasing_mass()
    assert ordered[0].mass_per_metre_kg_m <= ordered[-1].mass_per_metre_kg_m
    assert ordered[0].designation == "IPE-AA 100"  # 6.72 kg/m — the lightest in the set
