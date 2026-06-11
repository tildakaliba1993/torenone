"""Bolt properties + factored resistances — SANS 10162-1 cl. 13.12 (PROVISIONAL).

Resistance factors (SANS 10162-1 cl. 13.1):
    φb  = 0.80   (bolts — shear / tension)
    φbr = 0.80   (bolts — bearing on connected ply)

Per-bolt factored resistances (cl. 13.12.1.2 / 13.12.1.3), one bolt, one shear plane:
    Tension : Tr = 0.75 · φb · Ab · Fu_bolt
    Shear   : Vr = 0.60 · φb · Ab · Fu_bolt        (threads intercepted → Ab = stress area)
    Bearing : Br = 3.0  · φbr · t · d · Fu_ply

⚠️ PROVISIONAL — coefficients (0.75, 0.60, 3.0) and the φ values follow established
SANS 10162-1 / CSA S16 practice but were not transcribed from the standard PDF (absent
from `standards/`). Bolt tensile stress areas (Aₛ) are standard ISO metric coarse-thread
values. Engineer sign-off required before production use.
"""

from __future__ import annotations

import dataclasses

PHI_B: float = 0.80    # cl. 13.1 — bolts (PROVISIONAL)
PHI_BR: float = 0.80   # cl. 13.1 — bearing (PROVISIONAL)

# Bolt ultimate tensile strength by property class (MPa) — PROVISIONAL.
_GRADE_FU: dict[str, float] = {
    "8.8": 800.0,
    "10.9": 1000.0,
}

# ISO metric coarse-thread tensile stress area Aₛ (mm²) — standard geometric values.
_STRESS_AREA_MM2: dict[str, float] = {
    "M16": 157.0,
    "M20": 245.0,
    "M24": 353.0,
    "M30": 561.0,
}

# Nominal shank diameter (mm).
_DIAMETER_MM: dict[str, float] = {
    "M16": 16.0,
    "M20": 20.0,
    "M24": 24.0,
    "M30": 30.0,
}


@dataclasses.dataclass(frozen=True)
class BoltSpec:
    """A bolt size + grade with the properties needed for design."""

    designation: str        # e.g. "M20"
    diameter_mm: float
    stress_area_mm2: float  # tensile stress area Aₛ
    grade: str              # property class, e.g. "8.8"
    fu_mpa: float           # bolt ultimate strength


def make_bolt(size: str, grade: str) -> BoltSpec:
    """Build a :class:`BoltSpec` for a standard size (M16/M20/M24/M30) + grade (8.8/10.9)."""
    if size not in _STRESS_AREA_MM2:
        raise ValueError(f"Unknown bolt size {size!r}; expected one of {sorted(_STRESS_AREA_MM2)}")
    if grade not in _GRADE_FU:
        raise ValueError(f"Unknown bolt grade {grade!r}; expected one of {sorted(_GRADE_FU)}")
    return BoltSpec(
        designation=size,
        diameter_mm=_DIAMETER_MM[size],
        stress_area_mm2=_STRESS_AREA_MM2[size],
        grade=grade,
        fu_mpa=_GRADE_FU[grade],
    )


# Standard bolts available to the auto-designer, in ascending capacity order.
STANDARD_BOLTS: list[BoltSpec] = [
    make_bolt("M20", "8.8"),
    make_bolt("M24", "8.8"),
    make_bolt("M24", "10.9"),
    make_bolt("M30", "8.8"),
    make_bolt("M30", "10.9"),
]


def bolt_tension_resistance_kn(bolt: BoltSpec) -> float:
    """Factored tensile resistance of one bolt, Tr = 0.75·φb·Aₛ·Fu (cl. 13.12.1.2)."""
    tr_n = 0.75 * PHI_B * bolt.stress_area_mm2 * bolt.fu_mpa
    return float(tr_n / 1_000.0)


def bolt_shear_resistance_kn(bolt: BoltSpec, *, shear_planes: int = 1) -> float:
    """Factored shear resistance of one bolt, Vr = 0.60·φb·m·Aₛ·Fu (cl. 13.12.1.2).

    Uses the tensile stress area (threads assumed intercepted by the shear plane —
    the conservative case for an end-plate connection).
    """
    vr_n = 0.60 * PHI_B * shear_planes * bolt.stress_area_mm2 * bolt.fu_mpa
    return float(vr_n / 1_000.0)


def bolt_bearing_resistance_kn(bolt: BoltSpec, ply_thickness_mm: float, ply_fu_mpa: float) -> float:
    """Factored bearing resistance on the connected ply, Br = 3·φbr·t·d·Fu (cl. 13.12.1.3)."""
    br_n = 3.0 * PHI_BR * ply_thickness_mm * bolt.diameter_mm * ply_fu_mpa
    return float(br_n / 1_000.0)
