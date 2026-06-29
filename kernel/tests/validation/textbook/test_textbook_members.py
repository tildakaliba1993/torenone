"""Member-design validation vs an independent SECOND authority — Mahachi, *Design of Structural
Steelwork to SANS 10162* (CSIR, 2004; author J Mahachi Pr.Eng PhD; peer-reviewed by SA professors).

This complements the SAISC Red Book suite (kernel/tests/validation/redbook): where the Red Book
gives section data + capacity tables, this textbook gives fully worked SANS 10162 *design* examples
with boxed answers. Agreement here means **two respected, accredited SA sources independently
confirm the same kernel output** — which is exactly what shrinks the co-founder's job to "confirm
these authorities are appropriate." Only numeric facts are encoded (copyright respected); each case
cites its example. Must-pass.

Notable corroboration: the shear example (E5.1) computes the shear area as **overall depth × tw** —
the same basis as the Red Book (Ex 5.3). Two authorities now agree the shear area uses the overall
depth; the kernel pipeline currently uses the (more conservative) clear web depth. That remains a
flagged engineer decision (see docs/REDBOOK-VALIDATION.md), now with a second supporting source.
"""

from __future__ import annotations

import pytest
from torenone_kernel.checks.axial import cr_flexural
from torenone_kernel.checks.bending import mr_laterally_supported
from torenone_kernel.checks.classification import Class4Error, SectionClass, classify_section
from torenone_kernel.checks.shear import vr_web
from torenone_kernel.sections import SectionLibrary

_SRC = "Mahachi, Design of Structural Steelwork to SANS 10162 (CSIR, 2004)"
_TOL = 0.02

_LIB = SectionLibrary.load_default()


def test_compression_cr_e4_3() -> None:
    # E4.3: 356x171x67 I-section, Grade 300W, pinned, L=6000 mm → Cr = 589 kN (minor-axis flexural).
    cr = cr_flexural(area_mm2=8550, fy_mpa=300, KL_mm=6000, r_mm=39.9)
    assert cr == pytest.approx(589.0, rel=_TOL), f"{_SRC}, E4.3: Cr={cr:.0f} kN vs 589 kN"


def test_moment_resistance_supported_e5_1() -> None:
    # E5.1: 457x191x98, Class 1, laterally supported → Mr = φ·Zpl·fy = 602 kN·m.
    mr = mr_laterally_supported(SectionClass.CLASS1, 2230e3, 2000e3, 300.0)
    assert mr == pytest.approx(602.0, rel=_TOL), f"{_SRC}, E5.1: Mr={mr:.0f} kN·m vs 602 kN·m"


def test_shear_resistance_e5_1() -> None:
    # E5.1: 457x191x98 (tw=11.4), Vr = φ·Av·0.66·fy with Av = overall depth × tw = 950 kN.
    # (Fed the overall-depth basis the textbook + Red Book both use; the kernel pipeline's
    # clear-depth choice is ~12% more conservative — a flagged engineer decision.)
    vr = vr_web(467.6, 11.4, 300.0)
    assert vr == pytest.approx(950.0, rel=_TOL), f"{_SRC}, E5.1: Vr={vr:.0f} kN vs 950 kN"


@pytest.mark.parametrize("designation,expected", [("457x191x98", 1), ("356x171x67", 1)])
def test_classification(designation: str, expected: int) -> None:
    # E5.1 → 457x191x98 is Class 1; E4.3 → 356x171x67 is "not Class 4" (Class 1 here). fy=300 (300W).
    section = _LIB.get(designation)
    try:
        result = classify_section(section, 300.0, 0.0)
    except Class4Error:  # pragma: no cover - neither section is Class 4
        pytest.fail(f"{designation} unexpectedly Class 4")
    assert int(result.overall_class) == expected, (
        f"{_SRC}: {designation} Class {int(result.overall_class)} vs expected {expected}"
    )
