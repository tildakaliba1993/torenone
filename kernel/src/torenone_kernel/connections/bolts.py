"""Bolt properties + factored resistances — SANS 10162-1:2011 cl. 13.1 / 13.12.

Transcribed from the official SANS 10162-1:2011 (Ed 2.1) PDF (in `standards/`), 2026-06-15.

Resistance factors (cl. 13.1):
    φb  = 0.80   (c) bolts — shear / tension
    φbr = 0.67   (g) bearing of bolts on steel        ← corrected from 0.80 (was CSA value)

Per-bolt factored resistances — Ab is the bolt area based on its NOMINAL diameter
(cl. 3.2 symbols: "Ab = cross-sectional area of a bolt, based on its nominal diameter"),
i.e. the shank area π·d²/4. The 0.75 (tension) and 0.70 (threads-in-shear-plane) factors
are the standard's allowance for the threaded net area — so the shank area is correct here,
NOT the tensile stress area.
    Tension (cl. 13.12.1.3) : Tr = 0.75 · φb · Ab · fu
    Shear   (cl. 13.12.1.2) : Vr = 0.60 · φb · m · Ab · fu  (× 0.70 if threads intercept
                                                              the shear plane)
    Bearing (cl. 13.10(c) / 13.12.1.2) : Br = 3.0 · φbr · t · d · fu_ply

Bolt fu (cl. 13.12.1.2 NOTE): 830 MPa (class 8.8), 1040 MPa (class 10.9).

⚠️ PROVISIONAL — coefficients now match the official SANS 10162-1 text (verified clause by
clause), but final registered-engineer sign-off is still required before production use, and
the end-plate *method* (flange-force couple, simplified T-stub) remains an engineering
modelling choice (see moment_endplate.py).
"""

from __future__ import annotations

import dataclasses
import math

PHI_B: float = 0.80    # cl. 13.1(c) — bolts (shear / tension)
PHI_BR: float = 0.67   # cl. 13.1(g) / 13.10(c) — bearing of bolts on steel
PHI_AR: float = 0.67   # cl. 13.1(i) — holding-down (anchor) bolts

# When the bolt threads are intercepted by a shear plane, Vr is reduced by this factor
# (cl. 13.12.1.2). Typical for end-plate connections, so applied by default.
_THREADS_IN_SHEAR_PLANE_FACTOR: float = 0.70

# Bolt ultimate tensile strength by property class (MPa) — cl. 13.12.1.2 NOTE.
_GRADE_FU: dict[str, float] = {
    "8.8": 830.0,
    "10.9": 1040.0,
}

# ISO metric coarse-thread tensile stress area Aₛ (mm²) — standard geometric values.
# Retained as a documented bolt property; the SANS resistance formulas use the nominal
# (shank) area Ab, computed from the diameter (see cl. 3.2 symbols).
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
    stress_area_mm2: float  # tensile stress area Aₛ (documented; not used for resistance)
    grade: str              # property class, e.g. "8.8"
    fu_mpa: float           # bolt ultimate strength

    @property
    def shank_area_mm2(self) -> float:
        """Nominal (shank) cross-sectional area Ab = π·d²/4 — the area SANS uses (cl. 3.2)."""
        return math.pi * self.diameter_mm**2 / 4.0


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


def bolt_tension_resistance_kn(bolt: BoltSpec, *, phi: float = PHI_B) -> float:
    """Factored tensile resistance of one bolt, Tr = 0.75·φ·Ab·fu (cl. 13.12.1.3).

    Ab is the nominal (shank) area; the 0.75 factor is the standard's net-tensile-area
    allowance. *phi* defaults to φb (structural bolts); pass ``PHI_AR`` for holding-down
    (anchor) bolts (cl. 13.1(i)).
    """
    tr_n = 0.75 * phi * bolt.shank_area_mm2 * bolt.fu_mpa
    return float(tr_n / 1_000.0)


def bolt_shear_resistance_kn(
    bolt: BoltSpec,
    *,
    shear_planes: int = 1,
    threads_intercepted: bool = True,
    phi: float = PHI_B,
) -> float:
    """Factored shear resistance of one bolt, Vr = 0.60·φ·m·Ab·fu (cl. 13.12.1.2).

    Ab is the nominal (shank) area. When the threads are intercepted by the shear plane
    (the default, and the usual case for an end-plate connection), Vr is reduced by 0.70.
    *phi* defaults to φb; pass ``PHI_AR`` for holding-down (anchor) bolts (cl. 13.1(i)).
    """
    vr_n = 0.60 * phi * shear_planes * bolt.shank_area_mm2 * bolt.fu_mpa
    if threads_intercepted:
        vr_n *= _THREADS_IN_SHEAR_PLANE_FACTOR
    return float(vr_n / 1_000.0)


def bolt_bearing_resistance_kn(bolt: BoltSpec, ply_thickness_mm: float, ply_fu_mpa: float) -> float:
    """Factored bearing resistance on the connected ply, Br = 3·φbr·t·d·fu (cl. 13.10(c))."""
    br_n = 3.0 * PHI_BR * ply_thickness_mm * bolt.diameter_mm * ply_fu_mpa
    return float(br_n / 1_000.0)
