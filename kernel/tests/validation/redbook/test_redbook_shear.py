"""Shear resistance Vr vs SAISC Red Book Ex 5.3 / Table 5.13 (cl. 13.4.1.1).

Red Book Ex 5.3: a 533x210x82 (fy=350) beam has factored shear resistance Vr = 1050 kN.

⚠️ Av basis difference (flagged for the co-founder — see docs/REDBOOK-VALIDATION.md): the Red Book
computes the shear area as **overall depth × tw**, whereas the kernel pipeline uses the **clear web
depth** (hw = d − 2·tf), making it ~4–5% more conservative (≈1002 kN here). This case validates the
Vr *formula* (φ·Av·0.66·fy, with the inelastic-buckling branch) by feeding the Red Book's Av basis;
the clear-vs-overall depth choice is a code-interpretation item for the registered engineer.
"""

from __future__ import annotations

import pytest
from cases import RED_BOOK, RESISTANCE_REL_TOL
from torenone_kernel.checks.shear import vr_web
from torenone_kernel.sections import SectionLibrary

_LIB = SectionLibrary.load_default()


def test_shear_vr_formula() -> None:
    s = _LIB.get("533x210x82")
    # Feed the overall depth to match the Red Book's Av = depth × tw basis.
    vr = vr_web(s.depth_mm, s.web_thickness_mm, 350.0)
    assert vr == pytest.approx(1050.0, rel=RESISTANCE_REL_TOL), (
        f"533x210x82 ({RED_BOOK}, Ex 5.3): Vr = {vr:.0f} kN vs Red Book 1050 kN "
        f"({(vr - 1050.0) / 1050.0:+.1%})"
    )
