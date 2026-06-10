"""Shear resistance — SANS 10162-1:2011 cl. 13.4.1.1 (elastic analysis).

For rolled I-sections without transverse stiffeners (s → ∞ → kv = 5.34):

  If h/t ≤ 440·√(kv/fy):
      Vr = φ · Av · 0.66 · fy        [pure shear, no web buckling]  (VERIFIED, cl. 13.4.1.1a)

  If 440·√(kv/fy) < h/t ≤ 500·√(kv/fy):
      Vr = φ · Av · fcri              [inelastic shear buckling]     (VERIFIED, cl. 13.4.1.1b)

  For h/t beyond 500·√(kv/fy), tension-field action applies (cl. 13.4.1.1c/d). This range is
  rare for rolled sections and is flagged as a NotImplementedError if encountered.

Shear area Av = tw · hw  (VERIFIED — cl. 13.4.1.1: "tw·h for rolled steel sections")

φ = 0.90 (cl. 13.1a, VERIFIED)
E = 200 000 MPa (cl. 3.2, VERIFIED)
"""

from __future__ import annotations

import math

_PHI = 0.90
_KV_NO_STIFFENERS = 5.34   # kv for s→∞ (no transverse stiffeners), cl. 13.4.1.1a


def vr_web(
    hw_mm: float,
    tw_mm: float,
    fy_mpa: float,
    kv: float = _KV_NO_STIFFENERS,
) -> float:
    """Factored shear resistance of a rolled I-section web (cl. 13.4.1.1).

    Parameters
    ----------
    hw_mm  : clear web depth between flanges (mm)
    tw_mm  : web thickness (mm)
    fy_mpa : design yield stress (MPa)
    kv     : shear buckling coefficient (default 5.34 for no transverse stiffeners)

    Returns
    -------
    Vr in kN.
    """
    ht = hw_mm / tw_mm
    Av = tw_mm * hw_mm   # mm²

    # Slenderness limits
    lim1 = 440.0 * math.sqrt(kv / fy_mpa)   # pure shear limit
    lim2 = 500.0 * math.sqrt(kv / fy_mpa)   # inelastic buckling limit

    if ht <= lim1:
        # Pure shear — no web buckling (cl. 13.4.1.1a)
        fs = 0.66 * fy_mpa
    elif ht <= lim2:
        # Inelastic shear buckling (cl. 13.4.1.1b)
        fcri = (290.0 * math.sqrt(kv * fy_mpa)) / ht
        fs = fcri
    else:
        # Tension-field / elastic shear buckling — not implemented for MVP
        raise NotImplementedError(
            f"Web h/t = {ht:.1f} > {lim2:.1f} (kv={kv}, fy={fy_mpa} MPa). "
            "Tension-field shear range is outside the MVP scope — add transverse stiffeners "
            "or select a section with a stockier web."
        )

    return _PHI * Av * fs / 1_000.0   # N → kN
