"""Foundation design for the single-bay steel portal frame (Tasks 1.16 + 1.17).

Scope-limited to this one frame (PRD §6.1): column **baseplates** (pinned/fixed,
SANS 10162-1) and a simple **pad footing** (SANS 10100-1). NOT a general
foundation / geotechnical designer.

⚠️ PROVISIONAL — the SANS connection/concrete clauses were not available in
`standards/` when this was written; resistance formulas and coefficients follow
established SANS 10162-1 / CSA S16 / SANS 10100-1 practice and are flagged
PROVISIONAL pending a registered engineer's verification.
"""

from torenone_kernel.foundations.baseplate import (
    BasePlate,
    check_baseplate,
    design_baseplate,
)
from torenone_kernel.foundations.pad_footing import (
    PadFooting,
    check_pad_footing,
    design_pad_footing,
)

__all__ = [
    "BasePlate",
    "check_baseplate",
    "design_baseplate",
    "PadFooting",
    "check_pad_footing",
    "design_pad_footing",
]
