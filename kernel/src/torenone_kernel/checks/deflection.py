"""SLS deflection checks — SANS 10162-1:2011 Annex D (informative), Table D.1.

Annex D is **informative** (non-normative). These limits are widely adopted engineering
practice and are implemented as the default, but the engineer may override via the
`limit_fraction` parameter.

Confirmed limits (Table D.1, VERIFIED):
    Vertical deflection — inelastic roof coverings:  δ ≤ L/240
    Vertical deflection — elastic roof coverings:    δ ≤ L/180
    Building sway (all other buildings), wind:       Δ ≤ H/400

Note: the "H/400" sway limit in Table D.1 applies to "all other buildings" under wind.
Industrial portal frames without cranes are treated under this category. Engineers
sometimes use H/150 for portal frames; this is a practice value NOT stated in Annex D and
requires engineer sign-off. The default implemented here is H/400.
"""

from __future__ import annotations

from torenone_kernel.models.results import CheckResult


def vertical_deflection_check(
    delta_mm: float,
    span_mm: float,
    limit_fraction: int = 240,
) -> CheckResult:
    """Check rafter mid-span deflection under SLS variable loads.

    Parameters
    ----------
    delta_mm       : actual mid-span deflection (mm, positive downward)
    span_mm        : rafter span (mm)
    limit_fraction : denominator of the span fraction limit (default 240 for inelastic
                     roof covering per Annex D Table D.1; use 180 for elastic covering)

    Returns CheckResult with clause = Annex D.
    """
    limit_mm = span_mm / limit_fraction
    utilisation = delta_mm / limit_mm
    return CheckResult(
        name=f"Vertical deflection (SLS) — L/{limit_fraction}",
        clause=f"SANS 10162-1:2011 Annex D, Table D.1 (L/{limit_fraction})",
        utilisation=utilisation,
        passed=delta_mm <= limit_mm,
    )


def horizontal_sway_check(
    drift_mm: float,
    height_mm: float,
    limit_fraction: int = 400,
) -> CheckResult:
    """Check eaves lateral sway under SLS wind load.

    Default limit: H/400 (Annex D Table D.1 — "all other buildings", wind).

    Note: H/150 is sometimes used for industrial portal frames; use limit_fraction=150
    if the engineer specifies this. This requires explicit sign-off as it is not in Annex D.

    Parameters
    ----------
    drift_mm       : lateral eaves displacement (mm)
    height_mm      : eaves height (mm)
    limit_fraction : denominator (default 400 per Annex D)
    """
    limit_mm = height_mm / limit_fraction
    utilisation = drift_mm / limit_mm
    return CheckResult(
        name=f"Horizontal sway (SLS) — H/{limit_fraction}",
        clause=f"SANS 10162-1:2011 Annex D, Table D.1 (H/{limit_fraction})",
        utilisation=utilisation,
        passed=drift_mm <= limit_mm,
    )
