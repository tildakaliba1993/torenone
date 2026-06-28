"""SAISC Red Book component-validation — shared types + tolerances.

We benchmark the kernel's isolated, clause-tagged functions against published values from the
SAISC *Southern African Steel Construction Handbook* ("Red Book"), 8th ed. 2013 (based on
SANS 10162-1). Only **numeric facts** are encoded (copyright: no text/tables are reproduced); each
case cites its Red Book table/example. Tolerances follow ``docs/REFERENCES-AND-VALIDATION.md`` §4.

This is the **component** validation path (one isolated check at a time, vs the whole-frame
``benchmarks.py`` gate). It is co-founder-independent: the reference values are authoritative and
public, so these are **must-pass** tests, not skipped.

⚠️ Edition note: the Red Book 8th ed. is based on SANS 10162-1:**2005**; the kernel implements the
**2011** edition. Section geometry and the cl. 13.3/13.5/13.6 member-resistance equations are stable
across these editions. Bolt/connection clauses are **not** (the Red Book re-aligned Ch 6/7 to the
SAISC Green Book), so a connection mismatch may be an edition/basis difference, not a kernel bug —
record it in ``docs/REDBOOK-VALIDATION.md`` rather than "fixing" toward the older edition.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Tolerances (docs/REFERENCES-AND-VALIDATION.md §4) ---
SECTION_REL_TOL = 0.01  # section properties — published to ~3 s.f.; 1% catches parse/unit errors
RESISTANCE_REL_TOL = 0.05  # member/connection resistances — compound of forces + resistances
FORCE_REL_TOL = 0.02  # applied actions / member forces

RED_BOOK = "SAISC Red Book 8th ed. (2013)"


@dataclass(frozen=True)
class SectionCase:
    """One section's published properties (Red Book Table 2.9 I-sections/UB, 2.10 H-sections/UC).

    Base SI-mm units (mm, mm², mm³, mm⁴, mm⁶) — the Red Book's ``×10ⁿ`` scaling is applied here so
    the stored numbers compare directly against ``SectionProperties``. Any field left ``None`` is
    not asserted (e.g. a scanned table cell we can't read with confidence).
    """

    designation: str
    source: str
    area_mm2: float | None = None
    depth_mm: float | None = None
    width_mm: float | None = None
    web_t_mm: float | None = None
    flange_t_mm: float | None = None
    ix_mm4: float | None = None
    sx_mm3: float | None = None  # Red Book Ze (elastic modulus, major axis)
    zplx_mm3: float | None = None  # Red Book Zpl (plastic modulus, major axis)
    rx_mm: float | None = None
    iy_mm4: float | None = None
    ry_mm: float | None = None
    j_mm4: float | None = None
    cw_mm6: float | None = None
