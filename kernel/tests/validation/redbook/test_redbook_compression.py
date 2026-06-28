"""Axial compressive resistance Cr vs SAISC Red Book Chapter 4 worked examples (cl. 13.3.1).

Exercises ``checks/axial.py::cr_flexural`` against the Red Book's hand calculations. The Red Book
reads Cr/φA from a capacity table (Table 4.3, rounded to whole MPa); the kernel evaluates the
formula directly, so agreement is expected to ~1% (well within the resistance tolerance).
"""

from __future__ import annotations

import pytest
from cases import RED_BOOK, RESISTANCE_REL_TOL
from torenone_kernel.checks.axial import cr_flexural
from torenone_kernel.sections import SectionLibrary

_LIB = SectionLibrary.load_default()
_s203 = _LIB.get("203x133x30")

# (id, area_mm2, fy_mpa, KL_mm, r_mm, expected_Cr_kN, source)
CASES = [
    # Ex 4.1: 203x133x30 S355JR, L=2.5 m, K=0.8 (pinned-fixed) → KL=2000, governs about y-y.
    ("Ex4.1 203x133x30 KL=2000 (y-y)", _s203.area_mm2, 355.0, 2000.0,
     _s203.radius_gyration_ry_mm, 834.0, "Ex 4.1"),
    # Ex 4.3: 305x305x118 S355JR (fy=350 per the example), L=3.7 m, K=1.0.
    ("Ex4.3 305x305x118 Crx KL=3700", 15000.0, 350.0, 3700.0, 136.0, 4510.0, "Ex 4.3"),
    ("Ex4.3 305x305x118 Cry KL=3700", 15000.0, 350.0, 3700.0, 77.6, 3890.0, "Ex 4.3"),
]


@pytest.mark.parametrize(
    "name,area,fy,kl,r,expected,src", CASES, ids=[c[0] for c in CASES]
)
def test_compression_cr(
    name: str, area: float, fy: float, kl: float, r: float, expected: float, src: str
) -> None:
    cr = cr_flexural(area, fy, kl, r)
    assert cr == pytest.approx(expected, rel=RESISTANCE_REL_TOL), (
        f"{name} ({RED_BOOK}, {src}): cr_flexural = {cr:.0f} kN vs Red Book {expected:.0f} kN "
        f"({(cr - expected) / expected:+.1%})"
    )
