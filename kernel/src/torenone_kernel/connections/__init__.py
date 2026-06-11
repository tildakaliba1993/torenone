"""Connection design for the single-bay steel portal frame (Task 1.15).

Scope-limited to the two portal-frame moment joints — the **eaves (knee)** and the
**apex (ridge)** — designed as bolted end-plate moment connections (PRD §6.1). This is
NOT a general connection designer.

⚠️ PROVISIONAL: the SANS 10162-1 connection clauses were not available in `standards/`
when this was written, so the resistance formulas and coefficients here follow
established SANS 10162-1 / CSA S16 practice and are flagged PROVISIONAL pending a
registered engineer's verification against the standard. The flange-force-couple method
used is a recognised *simplified* moment-connection method (conservative for preliminary
design); it does not model prying, yield-line modes 2/3, or haunch geometry.
"""

from torenone_kernel.connections.bolts import (
    STANDARD_BOLTS,
    BoltSpec,
    bolt_bearing_resistance_kn,
    bolt_shear_resistance_kn,
    bolt_tension_resistance_kn,
)
from torenone_kernel.connections.moment_endplate import (
    EndPlateConnection,
    check_moment_connection,
    design_moment_connection,
)

__all__ = [
    "BoltSpec",
    "STANDARD_BOLTS",
    "bolt_tension_resistance_kn",
    "bolt_shear_resistance_kn",
    "bolt_bearing_resistance_kn",
    "EndPlateConnection",
    "check_moment_connection",
    "design_moment_connection",
]
