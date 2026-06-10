"""Wind actions per SANS 10160-3:2019 (Edition 2.1) — PRD FR-7.

All values are transcribed from the official standard (clause/table cited per item). The
velocity/pressure engine is validated against the standard's OWN Table 3 (cr vs height) in the
test suite — i.e. it reproduces the code's published table to within rounding.

Method (SANS 10160-3:2019, clauses 7.3–7.4):
  vp(z)   = cr(z) · co(z) · vb,peak                         (eq. 3)
  vb,peak = 1.0 · vb                                        (eq. 4)
  cr(z)   = 1.36 · ((z' − zo)/(zg − zo))^α,  z' = max(z, zc)  (eq. 5; params: Table 1)
  qp(z)   = ½ · ρ · vp²(z)                                  (eq. 6; ρ: Table 4 vs altitude)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from torenone_kernel.models.enums import TerrainCategory

# vb,peak = 1.0·vb — the map (Figure 1) is already a 3 s gust, no conversion (eq. 4 + NOTE).
PEAK_FACTOR = 1.0

# Fundamental basic wind-speed zones vb,0 (m/s), SANS 10160-3:2019 Figure 1 (3 s gust).
SA_BASIC_WIND_SPEED_ZONES_MS: tuple[float, ...] = (32.0, 36.0, 40.0, 44.0)


class TerrainParameters(BaseModel):
    """One row of SANS 10160-3:2019 Table 1 — Parameters of wind profile."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    zg_m: float = Field(gt=0, description="Gradient height.")
    zo_m: float = Field(ge=0, description="Height of the reference plane.")
    zc_m: float = Field(gt=0, description="Cut-off height (no further reduction below).")
    alpha: float = Field(gt=0, description="Profile exponent.")


# SANS 10160-3:2019 Table 1 — Parameters of wind profile (zg, zo, zc, α).
TERRAIN_PARAMETERS: dict[TerrainCategory, TerrainParameters] = {
    TerrainCategory.A: TerrainParameters(zg_m=250, zo_m=0, zc_m=1, alpha=0.070),
    TerrainCategory.B: TerrainParameters(zg_m=300, zo_m=0, zc_m=2, alpha=0.095),
    TerrainCategory.C: TerrainParameters(zg_m=350, zo_m=3, zc_m=5, alpha=0.120),
    TerrainCategory.D: TerrainParameters(zg_m=400, zo_m=5, zc_m=10, alpha=0.150),
}

# SANS 10160-3:2019 Table 4 — air density ρ (kg/m³) vs site altitude (m); linear interpolation.
_AIR_DENSITY_TABLE: tuple[tuple[float, float], ...] = (
    (0.0, 1.20),
    (500.0, 1.12),
    (1000.0, 1.06),
    (1500.0, 1.00),
    (2000.0, 0.94),
)


def air_density(site_altitude_m: float) -> float:
    """ρ (kg/m³) by linear interpolation of Table 4; clamped to its [0, 2000] m range."""
    pts = _AIR_DENSITY_TABLE
    if site_altitude_m <= pts[0][0]:
        return pts[0][1]
    if site_altitude_m >= pts[-1][0]:
        return pts[-1][1]
    for (a0, r0), (a1, r1) in zip(pts, pts[1:]):
        if a0 <= site_altitude_m <= a1:
            return r0 + (r1 - r0) * (site_altitude_m - a0) / (a1 - a0)
    return pts[-1][1]  # unreachable


def roughness_factor(z_m: float, category: TerrainCategory) -> float:
    """cr(z) per eq. (5) + Table 1; held constant at cr(zc) below the cut-off height zc."""
    p = TERRAIN_PARAMETERS[category]
    z_eff = max(z_m, p.zc_m)
    return 1.36 * ((z_eff - p.zo_m) / (p.zg_m - p.zo_m)) ** p.alpha


def peak_wind_speed(
    z_m: float,
    category: TerrainCategory,
    basic_wind_speed_ms: float,
    co: float = 1.0,
) -> float:
    """vp(z) = cr(z)·co·vb,peak, with vb,peak = 1.0·vb (eq. 3, 4)."""
    vb_peak = PEAK_FACTOR * basic_wind_speed_ms
    return roughness_factor(z_m, category) * co * vb_peak


def peak_velocity_pressure_kpa(vp_ms: float, air_density_kg_m3: float) -> float:
    """qp = ½·ρ·vp² (eq. 6), returned in kPa."""
    return 0.5 * air_density_kg_m3 * vp_ms**2 / 1000.0
