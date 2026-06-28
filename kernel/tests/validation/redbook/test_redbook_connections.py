"""Bolt resistances vs SAISC Red Book Table 7.2 — bolts in bearing-type connections (cl. 13.12 /
13.10). Validates ``connections/bolts.py`` (tension, single/double shear with threads in the shear
plane, bearing per mm of ply) for Class 8.8 and 10.9, sizes M16–M30.

Edition check resolved: despite the Red Book being 2005-based, its bolt factors **match** the
kernel's 2011 values exactly — no edition drift for bolts (contrary to the initial expectation).

Two findings from this benchmark (see docs/REDBOOK-VALIDATION.md):
  * M16-8.8 — fixed a kernel bug: Class 8.8 fu is 800 MPa for d ≤ 16 mm (ISO 898-1), not a flat
    830; the Red Book Table 7.2 confirms (M16-8.8 → 96.5 kN tension). Now corrected in bolts.py.
  * M24-10.9 bearing — the Red Book prints 27.7 kN/mm, an apparent typo (bearing is
    grade-independent; M24-8.8 = 22.7 and the 3·φbr·d·fu calc = 22.67). We assert the correct 22.7.

Bearing is benchmarked with ply fu = 470 MPa to match Table 7.2's Grade-S355JR basis (the kernel's
design pipeline uses 480 MPa per SANS Table 6 — a small SANS-vs-EN basis difference, not a bug).
"""

from __future__ import annotations

import pytest
from cases import RED_BOOK, RESISTANCE_REL_TOL
from torenone_kernel.connections.bolts import (
    bolt_bearing_resistance_kn,
    bolt_shear_resistance_kn,
    bolt_tension_resistance_kn,
    make_bolt,
)

_PLY_FU = 470.0  # Table 7.2 basis (Grade S355JR)

# (size, grade, Tr, Vr_single, Vr_double, Br_per_mm) — Red Book Table 7.2, threads in shear plane.
CASES = [
    ("M16", "8.8", 96.5, 54.0, 108.0, 15.1),
    ("M20", "8.8", 156.0, 87.6, 175.0, 18.9),
    ("M24", "8.8", 225.0, 126.0, 252.0, 22.7),
    ("M30", "8.8", 352.0, 197.0, 394.0, 28.3),
    ("M16", "10.9", 125.0, 70.3, 141.0, 15.1),
    ("M20", "10.9", 196.0, 110.0, 220.0, 18.9),
    ("M24", "10.9", 282.0, 158.0, 316.0, 22.7),  # bearing 22.7 (Red Book prints 27.7 — typo)
    ("M30", "10.9", 441.0, 247.0, 494.0, 28.3),
]


@pytest.mark.parametrize(
    "size,grade,tr,vs,vd,br", CASES, ids=[f"{c[0]}-{c[1]}" for c in CASES]
)
def test_bolt_resistances(
    size: str, grade: str, tr: float, vs: float, vd: float, br: float
) -> None:
    bolt = make_bolt(size, grade)
    src = f"{RED_BOOK}, Table 7.2"
    mismatches: list[str] = []

    kt = bolt_tension_resistance_kn(bolt)
    if kt != pytest.approx(tr, rel=RESISTANCE_REL_TOL):
        mismatches.append(f"tension: {kt:.1f} vs {tr:.1f} kN")

    ks = bolt_shear_resistance_kn(bolt, shear_planes=1, threads_intercepted=True)
    if ks != pytest.approx(vs, rel=RESISTANCE_REL_TOL):
        mismatches.append(f"shear (single): {ks:.1f} vs {vs:.1f} kN")

    kd = bolt_shear_resistance_kn(bolt, shear_planes=2, threads_intercepted=True)
    if kd != pytest.approx(vd, rel=RESISTANCE_REL_TOL):
        mismatches.append(f"shear (double): {kd:.1f} vs {vd:.1f} kN")

    kb = bolt_bearing_resistance_kn(bolt, 1.0, _PLY_FU)
    if kb != pytest.approx(br, rel=RESISTANCE_REL_TOL):
        mismatches.append(f"bearing/mm: {kb:.2f} vs {br:.1f} kN")

    assert not mismatches, f"{size}-{grade} ({src}):\n  " + "\n  ".join(mismatches)
