"""Axial compressive resistance — SANS 10162-1:2011 cl. 13.3.1.

Cr = φ · A · fy · (1 + λ^(2n))^(-1/n)

where:
    λ = (KL/r) · √(fy / (π²·E))     [non-dimensional slenderness]
    n = 1.34  for hot-rolled sections (cl. 13.3.1, VERIFIED)
    φ = 0.90  (cl. 13.1a, VERIFIED)
    E = 200 000 MPa (cl. 3.2, VERIFIED)

Slenderness limit: KL/r ≤ 200 (cl. 10.4.2.1, VERIFIED).
"""

from __future__ import annotations

import math

_E   = 200_000.0   # MPa — SANS 10162-1:2011 cl. 3.2 (VERIFIED)
_PHI = 0.90        # cl. 13.1a (VERIFIED)


class SlendernessError(ValueError):
    """Raised when KL/r > 200 (cl. 10.4.2.1 — compression slenderness limit)."""


def cr_flexural(
    area_mm2: float,
    fy_mpa: float,
    KL_mm: float,
    r_mm: float,
    n: float = 1.34,
) -> float:
    """Factored axial compressive resistance for flexural buckling (cl. 13.3.1).

    Parameters
    ----------
    area_mm2 : gross cross-sectional area (mm²)
    fy_mpa   : design yield stress (MPa)
    KL_mm    : effective length (mm) = K × L
    r_mm     : radius of gyration for the governing buckling axis (mm)
    n        : column curve parameter (default 1.34 for hot-rolled)

    Returns
    -------
    Cr in kN.
    """
    slenderness = KL_mm / r_mm
    if slenderness > 200.0:
        raise SlendernessError(
            f"KL/r = {slenderness:.1f} > 200 (cl. 10.4.2.1). "
            "Select a less slender column."
        )

    lam = slenderness * math.sqrt(fy_mpa / (math.pi**2 * _E))
    cr_n = _PHI * area_mm2 * fy_mpa * (1.0 + lam ** (2 * n)) ** (-1.0 / n)
    return float(cr_n / 1_000.0)   # N → kN
