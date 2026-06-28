"""Section-property validation vs SAISC Red Book Tables 2.9 (I-sections / UB) & 2.10 (UC).

Extends ``test_saisc_dataset.py`` from a 4-section spot-check to a broad spread across IPE-AA, IPE,
Universal Beams and Universal Columns — including J and Cw, which drive lateral-torsional buckling
(``checks/bending.py``). A mismatch means the packaged dataset disagrees with the printed Red Book
(parse / unit / notation error), or a transcription slip here — either way, investigate.
"""

from __future__ import annotations

import pytest
from cases import RED_BOOK, SECTION_REL_TOL, SectionCase
from torenone_kernel.sections import SectionLibrary

_T29 = f"{RED_BOOK}, Table 2.9"
_T210 = f"{RED_BOOK}, Table 2.10"

# Published values transcribed from the Red Book (×10ⁿ scaling applied → base mm units).
CASES: list[SectionCase] = [
    # --- IPE-AA / IPE (Table 2.9) ---
    SectionCase(
        "IPE-AA 100", _T29, area_mm2=856, depth_mm=97.6, width_mm=55, web_t_mm=3.6,
        flange_t_mm=4.5, ix_mm4=1.36e6, sx_mm3=27.8e3, zplx_mm3=31.9e3, rx_mm=39.8,
        iy_mm4=0.126e6, ry_mm=12.1, j_mm4=7.33e3, cw_mm6=0.272e9,
    ),
    SectionCase(
        "IPE 100", _T29, area_mm2=1030, depth_mm=100, width_mm=55, web_t_mm=4.1,
        flange_t_mm=5.7, ix_mm4=1.71e6, sx_mm3=34.2e3, zplx_mm3=39.4e3, rx_mm=40.7,
        iy_mm4=0.159e6, ry_mm=12.4, j_mm4=12.1e3, cw_mm6=0.354e9,
    ),
    SectionCase(
        "IPE 120", _T29, area_mm2=1320, depth_mm=120, width_mm=64, web_t_mm=4.4,
        flange_t_mm=6.3, ix_mm4=3.18e6, sx_mm3=53.0e3, zplx_mm3=60.7e3, rx_mm=49.0,
        iy_mm4=0.277e6, ry_mm=14.5, j_mm4=17.4e3, cw_mm6=0.894e9,
    ),
    SectionCase(
        "IPE 140", _T29, area_mm2=1640, depth_mm=140, width_mm=73, web_t_mm=4.7,
        flange_t_mm=6.9, ix_mm4=5.41e6, sx_mm3=77.3e3, zplx_mm3=88.3e3, rx_mm=57.4,
        iy_mm4=0.449e6, ry_mm=16.5, j_mm4=24.6e3, cw_mm6=1.99e9,
    ),
    SectionCase(
        "IPE 200", _T29, area_mm2=2850, depth_mm=200, width_mm=100, web_t_mm=5.6,
        flange_t_mm=8.5, ix_mm4=19.4e6, sx_mm3=194e3, zplx_mm3=221e3, rx_mm=82.6,
        iy_mm4=1.42e6, ry_mm=22.4, j_mm4=70.2e3, cw_mm6=13.1e9,
    ),
    # --- Universal Beams (Table 2.9) ---
    SectionCase(
        "203x133x25", _T29, area_mm2=3220, depth_mm=203.2, width_mm=133.2, web_t_mm=5.7,
        flange_t_mm=7.8, ix_mm4=23.5e6, sx_mm3=231e3, zplx_mm3=259e3, rx_mm=85.4,
        iy_mm4=3.09e6, ry_mm=31.0, j_mm4=59.0e3, cw_mm6=29.5e9,
    ),
    SectionCase(
        "203x133x30", _T29, area_mm2=3800, depth_mm=206.8, width_mm=133.9, web_t_mm=6.4,
        flange_t_mm=9.6, ix_mm4=28.9e6, sx_mm3=279e3, zplx_mm3=313e3, rx_mm=87.2,
        iy_mm4=3.84e6, ry_mm=31.8, j_mm4=103e3, cw_mm6=37.3e9,
    ),
    # --- Universal Columns / H-sections (Table 2.10) ---
    SectionCase(
        "152x152x23", _T210, area_mm2=2970, depth_mm=152.4, width_mm=152.4, web_t_mm=6.1,
        flange_t_mm=6.8, ix_mm4=12.6e6, sx_mm3=165e3, zplx_mm3=184e3, rx_mm=65.1,
        iy_mm4=4.02e6, ry_mm=36.8, j_mm4=51.5e3, cw_mm6=21.3e9,
    ),
    SectionCase(
        "203x203x46", _T210, area_mm2=5880, depth_mm=203.2, width_mm=203.2, web_t_mm=7.3,
        flange_t_mm=11.0, ix_mm4=45.6e6, sx_mm3=449e3, zplx_mm3=497e3, rx_mm=88.1,
        iy_mm4=15.4e6, ry_mm=51.6, j_mm4=225e3, cw_mm6=142e9,
    ),
    SectionCase(
        "254x254x73", _T210, area_mm2=9290, depth_mm=254.2, width_mm=254.0, web_t_mm=8.6,
        flange_t_mm=14.2, ix_mm4=114e6, sx_mm3=896e3, zplx_mm3=990e3,
        iy_mm4=38.8e6, ry_mm=64.6, j_mm4=578e3, cw_mm6=559e9,
    ),
    SectionCase(
        "305x305x97", _T210, area_mm2=12300, depth_mm=307.8, width_mm=304.8, web_t_mm=9.9,
        flange_t_mm=15.4, ix_mm4=222e6, sx_mm3=1440e3, zplx_mm3=1590e3, rx_mm=134,
        iy_mm4=72.7e6, ry_mm=76.8, j_mm4=919e3, cw_mm6=1550e9,
    ),
]

# Case field -> SectionProperties attribute.
_FIELD_MAP: dict[str, str] = {
    "area_mm2": "area_mm2",
    "depth_mm": "depth_mm",
    "width_mm": "width_mm",
    "web_t_mm": "web_thickness_mm",
    "flange_t_mm": "flange_thickness_mm",
    "ix_mm4": "second_moment_ix_mm4",
    "sx_mm3": "elastic_modulus_sx_mm3",
    "zplx_mm3": "plastic_modulus_zx_mm3",
    "rx_mm": "radius_gyration_rx_mm",
    "iy_mm4": "second_moment_iy_mm4",
    "ry_mm": "radius_gyration_ry_mm",
    "j_mm4": "torsion_constant_j_mm4",
    "cw_mm6": "warping_constant_cw_mm6",
}


@pytest.fixture(scope="module")
def lib() -> SectionLibrary:
    return SectionLibrary.load_default()


@pytest.mark.parametrize("case", CASES, ids=[c.designation for c in CASES])
def test_section_matches_red_book(lib: SectionLibrary, case: SectionCase) -> None:
    s = lib.get(case.designation)
    mismatches: list[str] = []
    for case_field, attr in _FIELD_MAP.items():
        expected = getattr(case, case_field)
        if expected is None:
            continue
        actual = getattr(s, attr)
        if actual != pytest.approx(expected, rel=SECTION_REL_TOL):
            delta = (actual - expected) / expected
            mismatches.append(f"{attr}: kernel={actual:g} vs RedBook={expected:g} ({delta:+.2%})")
    assert not mismatches, (
        f"{case.designation} ({case.source}) — section properties disagree with the Red Book "
        f"beyond ±{SECTION_REL_TOL:.0%}:\n  " + "\n  ".join(mismatches)
    )
