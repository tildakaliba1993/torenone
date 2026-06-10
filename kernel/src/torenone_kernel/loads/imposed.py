"""Characteristic imposed (variable) roof load per SANS 10160-2 (PRD FR-6).

⚠️ PROVISIONAL CODE VALUE — pending registered-engineer sign-off vs the official SANS 10160-2.
Source for the value below (free, authoritative):
  - SANS 10160-2:2011, Table 5 — inaccessible roof, normal maintenance & repair = 400 N/m².
  - Confirmed in a peer-reviewed open-access source: Journal of the South African Institution of
    Civil Engineering (SciELO, S1021-20192021000100005), which states the SANS 10160-2 Table 5
    inaccessible-roof value as 400 N/m², and corroborated across multiple independent references.

Scope (MVP): inaccessible roofs only — the standard portal-frame / warehouse case. Accessible
roofs reference occupancy-dependent categories whose values are not yet sourced/confirmed, so
they are out of scope here and raise a clear error.

Note: SANS 10160-2 also specifies a concentrated load (≈1.0 kN) for local element checks (e.g.
purlins); that is not part of the frame UDL and is out of scope for the frame analysis.
"""

from __future__ import annotations

from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import ImposedLoadResult

# SANS 10160-2:2011 Table 5 — inaccessible roof (normal maintenance & repair).
# PROVISIONAL: confirm against the official standard before the Phase 8 validation gate.
INACCESSIBLE_ROOF_QK_KPA = 0.4
_CLAUSE = "SANS 10160-2:2011 Table 5"


def imposed_roof_loads(spec: FrameSpec) -> ImposedLoadResult:
    """Compute the characteristic imposed roof load as a UDL on the rafter."""
    if spec.imposed.roof_access:
        raise NotImplementedError(
            "Accessible roofs are out of MVP scope — the SANS 10160-2 accessible-roof "
            "imposed value is not yet sourced/confirmed. Use an inaccessible roof."
        )
    tributary_m = spec.geometry.bay_spacing_m
    qk = INACCESSIBLE_ROOF_QK_KPA
    return ImposedLoadResult(
        roof_imposed_kpa=qk,
        tributary_width_m=tributary_m,
        roof_udl_kn_per_m=qk * tributary_m,
        category="Inaccessible roof — normal maintenance & repair",
        clause=_CLAUSE,
    )
