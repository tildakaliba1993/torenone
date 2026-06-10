"""Bending resistance — SANS 10162-1:2011 cl. 13.5 (laterally supported) and cl. 13.6 (LTB).

Laterally supported (cl. 13.5):
    Class 1/2: Mr = φ · Zpl · fy = φ · Mp      (VERIFIED)
    Class 3:   Mr = φ · Ze  · fy = φ · My      (VERIFIED)

Laterally unsupported — LTB (cl. 13.6a, doubly symmetric class 1/2 I-sections):
    Critical elastic moment (VERIFIED):
        Mcr = ω2 · (π/KL) · √(E·Iy · (G·J + π²·E·Cw / (KL)²))

    Mr:
        If Mcr > 0.67·Mp: Mr = 1.15·φ·Mp·(1 − 0.28·Mp/Mcr)  ≤  φ·Mp   (VERIFIED)
        If Mcr ≤ 0.67·Mp: Mr = φ·Mcr                                     (VERIFIED)

    For class 3 (cl. 13.6b), replace Mp with My.

ω2 moment gradient factor (cl. 13.6a):
    ω2 = 1.75 + 1.05·κ + 0.3·κ²  ≤ 2.5       (VERIFIED)
    where κ = ratio of smaller to larger end moment (+ve for double curvature)
    ω2 = 1.0 when bending moment at any point within the unbraced length exceeds the
         larger end moment, OR when there is no effective lateral support at one end.

Confirmed constants:
    E = 200 000 MPa (cl. 3.2, VERIFIED)
    G =  77 000 MPa (cl. 3.2, VERIFIED)
    φ  = 0.90 (cl. 13.1a, VERIFIED)
"""

from __future__ import annotations

import math

from torenone_kernel.checks.classification import SectionClass

_E   = 200_000.0   # MPa
_G   =  77_000.0   # MPa
_PHI = 0.90


def mr_laterally_supported(
    section_class: SectionClass,
    Zpl_mm3: float,
    Ze_mm3: float,
    fy_mpa: float,
) -> float:
    """Factored moment resistance assuming full lateral support (cl. 13.5).

    Returns Mr in kN·m.
    """
    if section_class in (SectionClass.CLASS1, SectionClass.CLASS2):
        return _PHI * Zpl_mm3 * fy_mpa / 1e6
    else:  # CLASS3
        return _PHI * Ze_mm3 * fy_mpa / 1e6


def omega2_factor(kappa: float) -> float:
    """Moment gradient factor ω2 (cl. 13.6a).

    Parameters
    ----------
    kappa : ratio of smaller to larger end moment at opposite ends of the unbraced length.
            Positive for double curvature; negative for single curvature.
            Use kappa = -1.0 to get ω2 = 1.0 (uniform moment, most conservative).
            Use 1.0 for UDL (mid-span > end moments → ω2 = 1.0 per cl. 13.6a).

    Returns
    -------
    ω2 ≤ 2.5
    """
    return min(1.75 + 1.05 * kappa + 0.3 * kappa**2, 2.5)


def mcr_elastic(
    KL_mm: float,
    Iy_mm4: float,
    J_mm4: float,
    Cw_mm6: float,
    omega2: float,
) -> float:
    """Critical elastic lateral-torsional buckling moment Mcr (cl. 13.6a).

    Mcr = ω2 · (π/KL) · √(E·Iy · (G·J + π²·E·Cw/(KL)²))

    Returns Mcr in kN·m.
    """
    term_gj  = _G * J_mm4
    term_ecw = math.pi**2 * _E * Cw_mm6 / KL_mm**2
    mcr_nmm  = omega2 * (math.pi / KL_mm) * math.sqrt(_E * Iy_mm4 * (term_gj + term_ecw))
    return mcr_nmm / 1e6  # N·mm → kN·m


def mr_ltb(
    section_class: SectionClass,
    Zpl_mm3: float,
    Ze_mm3: float,
    fy_mpa: float,
    mcr_knm: float,
) -> float:
    """Factored moment resistance accounting for LTB (cl. 13.6).

    Parameters
    ----------
    section_class : governs whether Mp or My is used
    Zpl_mm3       : plastic section modulus (mm³)
    Ze_mm3        : elastic section modulus (mm³)
    fy_mpa        : design yield stress (MPa)
    mcr_knm       : critical elastic LTB moment (kN·m) from mcr_elastic()

    Returns Mr in kN·m.
    """
    if section_class in (SectionClass.CLASS1, SectionClass.CLASS2):
        # Cl. 13.6a
        Mp_knm  = Zpl_mm3 * fy_mpa / 1e6          # kN·m (unfactored plastic moment)
        phi_Mp  = _PHI * Mp_knm
        if mcr_knm > 0.67 * Mp_knm:
            mr = 1.15 * phi_Mp * (1.0 - 0.28 * Mp_knm / mcr_knm)
            return min(mr, phi_Mp)
        else:
            return _PHI * mcr_knm
    else:
        # Cl. 13.6b — class 3 uses My
        My_knm  = Ze_mm3 * fy_mpa / 1e6
        phi_My  = _PHI * My_knm
        if mcr_knm > 0.67 * My_knm:
            mr = 1.15 * phi_My * (1.0 - 0.28 * My_knm / mcr_knm)
            return min(mr, phi_My)
        else:
            return _PHI * mcr_knm
