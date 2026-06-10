"""External pressure coefficients per SANS 10160-3:2019 clause 8.3 (PRD FR-7).

Values transcribed from the official standard (table extracted with structure-aware parsing, not
eyeballed) and validated against the standard's own tables in the test suite.

This module currently covers VERTICAL WALLS (Table 6). Duopitch roof coefficients (Table 10) are a
separate, larger step (5 zones, pitch interpolation, four load cases per its NOTE 1).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# SANS 10160-3:2019 Table 6 — cpe,10 (large areas) for vertical walls of rectangular buildings.
# We need the windward (zone D) and leeward (zone E) coefficients vs h/d.
_WALL_H_OVER_D: tuple[float, ...] = (0.25, 1.0, 5.0)
_WALL_CPE_WINDWARD: tuple[float, ...] = (0.7, 0.8, 0.8)  # zone D
_WALL_CPE_LEEWARD: tuple[float, ...] = (-0.3, -0.5, -0.7)  # zone E


def _interp(x: float, xs: tuple[float, ...], ys: tuple[float, ...]) -> float:
    """Piecewise-linear interpolation over breakpoints xs->ys, clamped at the ends."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[i], ys[i + 1]
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]  # unreachable


class WallPressureCoefficients(BaseModel):
    """External pressure coefficients (cpe,10) for the windward and leeward walls."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    cpe_windward: float = Field(description="Zone D (windward) cpe,10.")
    cpe_leeward: float = Field(description="Zone E (leeward) cpe,10.")
    lack_of_correlation_factor: float = Field(
        gt=0, description="Factor on the combined windward+leeward force (cl. 8.3.2.4)."
    )
    h_over_d: float = Field(gt=0)
    clause: str = Field(min_length=1)


def wall_pressure_coefficients(h_over_d: float) -> WallPressureCoefficients:
    """cpe,10 for windward (D) and leeward (E) walls at the given h/d (SANS 10160-3:2019 Table 6)."""
    return WallPressureCoefficients(
        cpe_windward=_interp(h_over_d, _WALL_H_OVER_D, _WALL_CPE_WINDWARD),
        cpe_leeward=_interp(h_over_d, _WALL_H_OVER_D, _WALL_CPE_LEEWARD),
        # cl. 8.3.2.4: combined windward+leeward force ×0.85 for h/d ≤ 1, ×1.0 for h/d ≥ 5, interp.
        lack_of_correlation_factor=_interp(h_over_d, (1.0, 5.0), (0.85, 1.0)),
        h_over_d=h_over_d,
        clause="SANS 10160-3:2019 Table 6 + cl. 8.3.2.4",
    )


# --- Duopitch roof, θ = 0° (SANS 10160-3:2019 Table 10) ---------------------------------------
# MVP scope: typical INTERNAL frame — zones H (windward slope) and I (leeward slope), positive
# pitch 5°–45° (the common portal range). Values cross-checked against EN 1991-1-4 Table 7.4a,
# which SANS adopts. Deferred post-MVP: gable-edge zones F/G, ridge zone J, near-flat roofs
# (<5°, flat-roof provisions) and steep roofs (>45°).
_ROOF_PITCH_DEG: tuple[float, ...] = (5.0, 15.0, 30.0, 45.0)
_H_SUCTION: tuple[float, ...] = (-0.6, -0.3, -0.2, -0.0)  # windward (H), negative/uplift branch
_H_PRESSURE: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6)  # windward (H), positive/downforce branch
_I_SUCTION: tuple[float, ...] = (-0.6, -0.4, -0.4, -0.2)  # leeward (I), negative branch


class RoofPressureCoefficients(BaseModel):
    """cpe,10 for the windward (H) and leeward (I) duopitch roof slopes (θ = 0°).

    The windward slope has two cases (Table 10 NOTE 1): suction (uplift) and pressure (downforce).
    The frame-loads stage (1.6d) combines these into the governing wind load cases.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    windward_cpe_suction: float = Field(description="Zone H, negative (uplift) branch.")
    windward_cpe_pressure: float = Field(description="Zone H, positive (downforce) branch.")
    leeward_cpe_suction: float = Field(description="Zone I, negative branch.")
    pitch_deg: float = Field(gt=0)
    clause: str = Field(min_length=1)


def duopitch_roof_pressure_coefficients(pitch_deg: float) -> RoofPressureCoefficients:
    """cpe,10 for a duopitch roof (θ = 0°), zones H & I, by pitch (SANS 10160-3:2019 Table 10)."""
    if not (5.0 <= pitch_deg <= 45.0):
        raise NotImplementedError(
            "Duopitch roof cpe is implemented for pitch 5°–45° (typical portal range). "
            "Near-flat (<5°) and steep (>45°) roofs are out of MVP scope."
        )
    return RoofPressureCoefficients(
        windward_cpe_suction=_interp(pitch_deg, _ROOF_PITCH_DEG, _H_SUCTION),
        windward_cpe_pressure=_interp(pitch_deg, _ROOF_PITCH_DEG, _H_PRESSURE),
        leeward_cpe_suction=_interp(pitch_deg, _ROOF_PITCH_DEG, _I_SUCTION),
        pitch_deg=pitch_deg,
        clause="SANS 10160-3:2019 Table 10 (θ=0°, zones H & I)",
    )


# --- Internal pressure, cpi (SANS 10160-3:2019 cl. 8.3.9) -------------------------------------
# Enclosed (no dominant wall): cl. 8.3.9.6 NOTE 2 — where μ is not estimated, take cpi as the more
# onerous of +0.2 and −0.3 (both cases considered). The μ/Figure-16 refinement is deferred post-MVP.
ENCLOSED_CPI_CASES: tuple[float, ...] = (0.2, -0.3)


class InternalPressureCoefficients(BaseModel):
    """The cpi value(s) to consider for the building — each becomes a wind load case."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    cpi_cases: tuple[float, ...] = Field(min_length=1, description="cpi values to consider.")
    scenario: str = Field(min_length=1)
    clause: str = Field(min_length=1)


def enclosed_internal_pressure() -> InternalPressureCoefficients:
    """cpi for an enclosed building with no dominant opening (cl. 8.3.9.6 NOTE 2)."""
    return InternalPressureCoefficients(
        cpi_cases=ENCLOSED_CPI_CASES,
        scenario="enclosed (no dominant opening)",
        clause="SANS 10160-3:2019 cl. 8.3.9.6 (NOTE 2: more onerous of +0.2 and −0.3)",
    )


def dominant_opening_internal_pressure(
    cpe_at_opening: float, openings_at_least_3x: bool = False
) -> InternalPressureCoefficients:
    """cpi for a building with a dominant opening (cl. 8.3.9.5, eq. 14/15).

    `cpe_at_opening` is the external pressure coefficient at the dominant opening (e.g. the windward
    wall cpe for a windward roller door — the case that drives interior over-pressure / roof uplift).
    cl. 8.3.9.1: when cpi is favourable, an additional case with cpi = 0 is also considered.
    """
    factor = 0.90 if openings_at_least_3x else 0.75
    return InternalPressureCoefficients(
        cpi_cases=(factor * cpe_at_opening, 0.0),
        scenario=f"dominant opening (cpi = {factor:.2f}·cpe)",
        clause="SANS 10160-3:2019 cl. 8.3.9.5 (eq. 14/15) + cl. 8.3.9.1",
    )
