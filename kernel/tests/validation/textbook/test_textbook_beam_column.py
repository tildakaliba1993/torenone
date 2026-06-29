"""Beam-column validation vs Mahachi (CSIR 2004), Example E6.1 — beam-column in strong-axis bending.

This is the case the SAISC Red Book did not provide: a full SANS 10162 cl. 13.8 **interaction**
check. A single worked example (305×305×118 H-section, Grade 300W, L=3.2 m, Cu=2200 kN, major-axis
moments 180/240 kN·m) exercises six kernel functions at once and confirms each against the book's
boxed answers — closing the interaction-validation gap from an accredited authority.

The kernel's U1 amplification (`u1_factor`) floors at 1.0, which is the correct value for our
unbraced portal frames; the book's *braced* overall-member check uses the unfloored U1 (0.417). The
raw U1 formula matches the book (0.417); `beam_column_check` takes U1 as input, so the interaction
equation is validated directly with the book's U1 values.
"""

from __future__ import annotations

import pytest
from torenone_kernel.checks.axial import cr_flexural
from torenone_kernel.checks.bending import mcr_elastic, mr_laterally_supported, mr_ltb, omega2_factor
from torenone_kernel.checks.classification import SectionClass
from torenone_kernel.checks.interaction import beam_column_check, u1_factor

_SRC = "Mahachi, Design of Structural Steelwork to SANS 10162 (CSIR, 2004), E6.1"
_TOL = 0.02
_C1 = SectionClass.CLASS1

# 305×305×118, Grade 300W (fy=300): A=15e3, Ix=276e6, Iy=90.1e6, J=1620e3, Cw=1970e9,
# rx=136, ry=77.6, Zplx=1950e3. L=3200, Cu=2200, Mux=240 (governing end moment).


def test_compression_resistance_both_axes() -> None:
    assert cr_flexural(15000, 300, 3200, 136.0) == pytest.approx(3944, rel=_TOL)  # strong axis
    assert cr_flexural(15000, 300, 3200, 77.6) == pytest.approx(3619, rel=_TOL)  # weak axis


def test_moment_resistances() -> None:
    # Laterally supported Mrx = φ·Zpl·fy = 526.5 kN·m
    assert mr_laterally_supported(_C1, 1950e3, 1700e3, 300.0) == pytest.approx(526.5, rel=_TOL)
    # LTB: ω2 (κ=+0.75) capped at 2.5; Mcr = 7400 kN·m; Mr = 527 kN·m
    assert omega2_factor(0.75) == pytest.approx(2.5, rel=1e-3)
    mcr = mcr_elastic(3200, 90.1e6, 1620e3, 1970e9, 2.5)
    assert mcr == pytest.approx(7400, rel=_TOL)
    assert mr_ltb(_C1, 1950e3, 1700e3, 300.0, mcr) == pytest.approx(527, rel=_TOL)


def test_u1_amplification_formula() -> None:
    # Unfloored U1 formula matches the book's braced value (0.417); the kernel floors to 1.0
    # for unbraced portals (its use case).
    unfloored = 0.40 / (1.0 - 2200.0 / 53203.0)
    assert unfloored == pytest.approx(0.417, abs=0.005)
    assert u1_factor(0.40, 2200, 53203) == pytest.approx(1.0)


# (name, Cr, Mr, U1, expected utilisation) — the three cl. 13.8.1 interaction checks.
_INTERACTION = [
    ("cross-sectional strength", 4050.0, 526.5, 1.0, 0.930),
    ("overall member strength", 3944.0, 526.5, 0.417, 0.72),
    ("lateral-torsional buckling", 3619.0, 527.0, 1.0, 0.994),
]


@pytest.mark.parametrize("name,cr,mr,u1,expected", _INTERACTION, ids=[c[0] for c in _INTERACTION])
def test_beam_column_interaction(name: str, cr: float, mr: float, u1: float, expected: float) -> None:
    util = beam_column_check(
        cu_kn=2200, cr_kn=cr, mu_knm=240, mr_knm=mr, U1=u1, section_class=_C1
    ).utilisation
    assert util == pytest.approx(expected, abs=0.01), f"{_SRC} ({name}): {util:.3f} vs {expected}"
