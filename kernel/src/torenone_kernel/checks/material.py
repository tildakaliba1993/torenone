"""Steel material properties for design.

fy for S355JR (EN 10025-2, referenced in SANS 10162-1:2011 cl. 5.1.3):
    t ≤ 16 mm :   355 MPa   (PROVISIONAL — pending engineer sign-off vs SANS 1431 / EN 10025-2)
    16 < t ≤ 40mm: 345 MPa  (PROVISIONAL)
    40 < t ≤ 63mm: 335 MPa  (PROVISIONAL)

fy for S275JR (EN 10025-2):
    t ≤ 16 mm :   275 MPa   (PROVISIONAL)
    16 < t ≤ 40mm: 265 MPa  (PROVISIONAL)
    40 < t ≤ 63mm: 255 MPa  (PROVISIONAL)

The standard (cl. 5.1.2) requires using specified minimum values from the relevant material
standard. SANS 10162-1 references both SANS 1431 (grade 300) and EN 10025 (grade 355). These
values match EN 10025-2:2004 Table 7. Engineer sign-off required before production use.
"""

from __future__ import annotations

from torenone_kernel.models.enums import SteelGrade

# fy tables: thickness_limit_mm -> fy_MPa (ordered, use first threshold that fits)
_FY_TABLES: dict[SteelGrade, list[tuple[float, float]]] = {
    SteelGrade.S355JR: [
        (16.0,  355.0),
        (40.0,  345.0),
        (63.0,  335.0),
    ],
    SteelGrade.S275JR: [
        (16.0,  275.0),
        (40.0,  265.0),
        (63.0,  255.0),
    ],
}


def fy_mpa(grade: SteelGrade, thickness_mm: float) -> float:
    """Return design yield stress fy (MPa) for the given grade and element thickness.

    Uses the nominal thickness of the governing element (flange for beams, generally).
    Values are PROVISIONAL — pending registered-engineer sign-off vs SANS 1431 / EN 10025-2.

    Raises ValueError for thickness > 63 mm (out of MVP scope for these grades).
    """
    table = _FY_TABLES.get(grade)
    if table is None:
        raise ValueError(f"Unknown steel grade: {grade!r}")
    for t_limit, fy in table:
        if thickness_mm <= t_limit:
            return fy
    raise ValueError(
        f"Flange thickness {thickness_mm:.1f} mm > 63 mm for {grade.value}: "
        "out of MVP scope (cl. 5.1.3 — verify with engineer for heavy sections)."
    )
