"""Flexural resistance vs SAISC Red Book worked examples — laterally supported (cl. 13.5) and
lateral-torsional buckling (cl. 13.6).

Exercises ``checks/bending.py`` (``mr_laterally_supported``, ``mcr_elastic``, ``mr_ltb``,
``omega2_factor``) against Red Book Ch 4 (Ex 4.3) and Ch 5 (Ex 5.1, 5.2). LTB section properties
(Iy, J, Cw) come from the library, which the sections suite validates against Red Book Table 2.9.
"""

from __future__ import annotations

import pytest
from cases import RED_BOOK, RESISTANCE_REL_TOL
from torenone_kernel.checks.bending import (
    mcr_elastic,
    mr_laterally_supported,
    mr_ltb,
    omega2_factor,
)
from torenone_kernel.checks.classification import SectionClass
from torenone_kernel.sections import SectionLibrary

_LIB = SectionLibrary.load_default()


def test_omega2_uniform_moment_gradient() -> None:
    # Red Book Ex 5.2 / Table 5.4: κ = 0 (moment zero at one end) → ω2 = 1.75.
    assert omega2_factor(0.0) == pytest.approx(1.75, rel=1e-3)


# --- Laterally supported (cl. 13.5): Mr = φ·Zpl·fy --------------------------------------------
# (id, class, Zpl_mm3, Ze_mm3, fy, expected_Mr_kNm, source)  — Ex 4.3 305x305x118, fy=350.
_SUPPORTED = [
    ("Ex4.3 305x305x118 Mrx", SectionClass.CLASS2, 1950e3, 1760e3, 350.0, 614.0, "Ex 4.3"),
    ("Ex4.3 305x305x118 Mry", SectionClass.CLASS2, 892e3, 580e3, 350.0, 281.0, "Ex 4.3"),
]


@pytest.mark.parametrize(
    "name,cls,zpl,ze,fy,expected,src", _SUPPORTED, ids=[c[0] for c in _SUPPORTED]
)
def test_mr_laterally_supported(
    name: str, cls: SectionClass, zpl: float, ze: float, fy: float, expected: float, src: str
) -> None:
    mr = mr_laterally_supported(cls, zpl, ze, fy)
    assert mr == pytest.approx(expected, rel=RESISTANCE_REL_TOL), (
        f"{name} ({RED_BOOK}, {src}): Mr = {mr:.0f} kN·m vs Red Book {expected:.0f} kN·m"
    )


# --- Lateral-torsional buckling (cl. 13.6): 533x210x122, Class 1, fy=350 ----------------------
_S533 = _LIB.get("533x210x122")
# (id, KL_mm, omega2, expected_Mcr_kNm | None, expected_Mr_kNm, source)
_LTB = [
    ("Ex5.2 533x210x122 KL=5000 ω2=1.75", 5000.0, 1.75, 1625.0, 929.0, "Ex 5.2"),
    ("Ex5.1 533x210x122 KL=10000 ω2=1.0", 10000.0, 1.0, None, 317.0, "Ex 5.1"),
]


@pytest.mark.parametrize(
    "name,kl,w2,expected_mcr,expected_mr,src", _LTB, ids=[c[0] for c in _LTB]
)
def test_mr_ltb(
    name: str, kl: float, w2: float, expected_mcr: float | None, expected_mr: float, src: str
) -> None:
    mcr = mcr_elastic(
        kl,
        _S533.second_moment_iy_mm4,
        _S533.torsion_constant_j_mm4,
        _S533.warping_constant_cw_mm6,
        w2,
    )
    if expected_mcr is not None:
        assert mcr == pytest.approx(expected_mcr, rel=RESISTANCE_REL_TOL), (
            f"{name} ({RED_BOOK}, {src}): Mcr = {mcr:.0f} kN·m vs Red Book {expected_mcr:.0f}"
        )
    mr = mr_ltb(
        SectionClass.CLASS1,
        _S533.plastic_modulus_zx_mm3,
        _S533.elastic_modulus_sx_mm3,
        350.0,
        mcr,
    )
    assert mr == pytest.approx(expected_mr, rel=RESISTANCE_REL_TOL), (
        f"{name} ({RED_BOOK}, {src}): Mr = {mr:.0f} kN·m vs Red Book {expected_mr:.0f} kN·m"
    )
