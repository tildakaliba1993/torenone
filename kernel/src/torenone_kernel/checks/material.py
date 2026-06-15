"""Steel material properties for design.

fy/fu basis: SANS 10162-1:2011 cl. 5.1.2 requires the specified minimum values from the
relevant material standard; cl. 5.1.3 lists SANS 1431 (grade 300) and EN 10025 (grade 355).

fy (minimum yield ReH) — ✅ VERIFIED vs EN 10025-2:2019 Table 6, 2026-06-15:
    S355JR :  t ≤ 16 mm = 355 · >16≤40 = 345 · >40≤63 = 335 MPa
    S275JR :  t ≤ 16 mm = 275 · >16≤40 = 265 · >40≤63 = 255 MPa
All three thickness bands for both grades match EN 10025-2:2019 Table 6 exactly; the S355JR
base (355) is also independently confirmed by SANS 10162-1:2011 Table 6.

Tensile fu: EN 10025-2 Table 6 gives S355 Rm = 470–630 MPa (3–100 mm) ⇒ min 470; the kernel's
connection/weld fu (480 MPa) is the SANS 10162-1 Table 6 value (slightly higher than the EN
minimum — the SA standard governs SA design).

Final registered-engineer sign-off remains good practice, but the values are now confirmed
against the source material standard (our EN 10025-2:2019 copy is genuine BSI/CEN content
obtained via a re-host — licensing copy is a separate procurement item).
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
    Values VERIFIED vs EN 10025-2:2019 Table 6 (see module docstring); Pr.Eng sign-off remains
    good practice.

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
