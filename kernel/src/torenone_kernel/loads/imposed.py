"""Characteristic imposed (variable) roof load per SANS 10160-2 (PRD FR-6).

✅ VERIFIED against SANS 10160-2:2011 Table 5 (2026-06-15).

Category H2 — inaccessible roof, *normal maintenance and repair* (the persistent in-service
design case). The minimum characteristic UDL is **area-dependent** on the loaded area A
(the projected roof area carried by the member under consideration — cl. 9.3.4.6 + Table 5
footnote a):
    qk = 0.50 kN/m²            for A ≤ 3 m²
    qk = 0.25 kN/m²            for A ≥ 15 m²
    qk = 0.25 + (15 − A)/48    for 3 m² < A < 15 m²   (linear interpolation)
For a typical portal frame the rafter's projected tributary area (bay × span/2) far exceeds
15 m², so qk = 0.25 kN/m². (H1 "during construction" — 0.75→0.25 — is a transient construction
load, not the persistent design case, so it is out of scope here.)

Scope (MVP): inaccessible roofs only — the standard portal-frame / warehouse case. Accessible
roofs (categories J/K) reference occupancy-dependent values out of scope here; they raise.

Note: SANS 10160-2 Table 5 also specifies a concentrated load Qk (≈1.0 kN over 0.1×0.1 m) for
local element checks (e.g. purlins); that is not part of the frame UDL and is out of scope for
the frame analysis.
"""

from __future__ import annotations

from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import ImposedLoadResult

# SANS 10160-2:2011 Table 5, category H2 (inaccessible roof, normal maintenance & repair).
H2_QK_SMALL_AREA_KPA = 0.50   # A ≤ 3 m²
H2_QK_LARGE_AREA_KPA = 0.25   # A ≥ 15 m²
_H2_AREA_SMALL_M2 = 3.0
_H2_AREA_LARGE_M2 = 15.0
_CLAUSE = "SANS 10160-2:2011 Table 5 (category H2)"


def inaccessible_roof_qk_kpa(loaded_area_m2: float) -> float:
    """Category-H2 minimum imposed roof load qk (kN/m²) for the given loaded area.

    SANS 10160-2:2011 Table 5: 0.50 for A ≤ 3 m², 0.25 for A ≥ 15 m², linearly interpolated
    (qk = 0.25 + (15 − A)/48) in between. A is the projected roof area carried by the member.
    """
    if loaded_area_m2 <= _H2_AREA_SMALL_M2:
        return H2_QK_SMALL_AREA_KPA
    if loaded_area_m2 >= _H2_AREA_LARGE_M2:
        return H2_QK_LARGE_AREA_KPA
    return H2_QK_LARGE_AREA_KPA + (_H2_AREA_LARGE_M2 - loaded_area_m2) / 48.0


def imposed_roof_loads(spec: FrameSpec) -> ImposedLoadResult:
    """Compute the characteristic imposed roof load as a UDL on the rafter."""
    if spec.imposed.roof_access:
        raise NotImplementedError(
            "Accessible roofs are out of MVP scope — the SANS 10160-2 accessible-roof "
            "imposed value is not yet sourced/confirmed. Use an inaccessible roof."
        )
    tributary_m = spec.geometry.bay_spacing_m
    # Loaded area for the rafter under consideration = projected roof tributary area
    # = bay spacing × half-span (each rafter carries half the bay's roof, eaves→apex).
    loaded_area_m2 = tributary_m * (spec.geometry.span_m / 2.0)
    qk = inaccessible_roof_qk_kpa(loaded_area_m2)
    return ImposedLoadResult(
        roof_imposed_kpa=qk,
        tributary_width_m=tributary_m,
        roof_udl_kn_per_m=qk * tributary_m,
        category=(
            f"Inaccessible roof H2 (normal maintenance & repair); "
            f"loaded area {loaded_area_m2:.1f} m²"
        ),
        clause=_CLAUSE,
    )
