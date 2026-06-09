"""Enumerations for the frame domain model.

Values that map to specific code coefficients (steel grade -> yield strength; terrain category
-> roughness parameters) are resolved later in the kernel, against the verified SANS standards.
The enums here only capture the *choice*, not the engineering number.
"""

from __future__ import annotations

from enum import Enum


class BaseFixity(str, Enum):
    PINNED = "pinned"
    # FIXED is forward-compat only — the MVP kernel supports PINNED bases (PRD §6.1).
    FIXED = "fixed"


class SteelGrade(str, Enum):
    S275JR = "S275JR"
    S355JR = "S355JR"


class TerrainCategory(str, Enum):
    # VERIFY labels/definitions against SANS 10160-3 — SA terrain categories differ from Eurocode.
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class LimitState(str, Enum):
    ULS = "ULS"  # ultimate limit state (strength)
    SLS = "SLS"  # serviceability limit state (deflection)


class LoadType(str, Enum):
    DEAD = "dead"
    IMPOSED = "imposed"
    WIND = "wind"
