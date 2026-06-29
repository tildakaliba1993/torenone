"""Pluggable design codes. The kernel is code-agnostic: the orchestrator depends on the
`DesignCode` interface, and a code is selected per design. SANS 10162-1 is the default and, for
now, the only implementation; AISC 360 is the planned second code (see docs/PLAN/PHASE notes).
"""

from __future__ import annotations

from torenone_kernel.codes.base import DesignCode
from torenone_kernel.codes.sans10162 import SANS10162

#: The default code used when a caller does not specify one (keeps every existing call site working).
DEFAULT_CODE: DesignCode = SANS10162()

#: Registry for code selection (Phase 3 — user picks their country's code).
CODES: dict[str, type[DesignCode]] = {SANS10162.id: SANS10162}

__all__ = ["CODES", "DEFAULT_CODE", "DesignCode", "SANS10162"]
