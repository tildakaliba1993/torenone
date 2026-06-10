"""Wind actions per SANS 10160-3 (PRD FR-7).

This module is built in layers:
  1. Velocity/pressure ENGINE — the formulas (roughness factor, peak wind speed, peak velocity
     pressure). These are public/Eurocode-aligned and fully tested here.
  2. SANS-specific TERRAIN DATA (z0, zmin per category) + the vb,peak factor + air density ρ —
     these are the detailed content of SANS 10160-3 Tables 1 & 2 and are NOT available in any
     legitimate free source (see SOURCES.md E7). They are intentionally left PENDING: the
     registry below is empty, so any attempt to use a SANS terrain category raises a clear error
     until the registered engineer supplies the ~12 values. NOTHING is fabricated.

Method (SANS 10160-3, aligned with EN 1991-1-4):
  cr(z) = kr · ln(z/z0)         for zmin ≤ z ≤ zmax   (cr held at cr(zmin) below zmin)
  kr    = 0.19 · (z0 / z0_II)^0.07,  z0_II = 0.05 m    (EN 1991-1-4 form)
  vp(z) = cr(z) · co(z) · vb,peak
  qp(z) = ½ · ρ · vp(z)²
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from torenone_kernel.models.enums import TerrainCategory

_Z0_REFERENCE_M = 0.05  # terrain category II reference roughness length (EN 1991-1-4)

# SANS fundamental basic wind-speed zones vb,0 (m/s) at 10 m in terrain category B.
# Sourced (peer-reviewed SciELO); PROVISIONAL — see SOURCES.md E5.
SA_BASIC_WIND_SPEED_ZONES_MS: tuple[float, ...] = (32.0, 36.0, 40.0, 44.0)


# --- 1. Velocity / pressure engine (public formulas — fully tested) -------------------------


def kr_from_z0(z0_m: float, z0_reference_m: float = _Z0_REFERENCE_M) -> float:
    """Terrain factor kr = 0.19·(z0/z0,II)^0.07 (EN 1991-1-4 form)."""
    return 0.19 * (z0_m / z0_reference_m) ** 0.07


def roughness_factor(z_m: float, *, z0_m: float, zmin_m: float, kr: float) -> float:
    """cr(z) = kr·ln(z/z0), held constant at cr(zmin) for z < zmin."""
    z = max(z_m, zmin_m)
    return kr * math.log(z / z0_m)


def peak_wind_speed(
    z_m: float,
    *,
    z0_m: float,
    zmin_m: float,
    vb_peak_ms: float,
    kr: float | None = None,
    co: float = 1.0,
) -> float:
    """vp(z) = cr(z)·co·vb,peak. kr defaults to the EN form if not supplied."""
    if kr is None:
        kr = kr_from_z0(z0_m)
    return roughness_factor(z_m, z0_m=z0_m, zmin_m=zmin_m, kr=kr) * co * vb_peak_ms


def peak_velocity_pressure_kpa(vp_ms: float, rho_kg_m3: float) -> float:
    """qp = ½·ρ·vp²  (Pa), returned in kPa."""
    return 0.5 * rho_kg_m3 * vp_ms**2 / 1000.0


# --- 2. SANS-specific terrain data (PENDING — see SOURCES.md E7) -----------------------------


class TerrainParameters(BaseModel):
    """SANS 10160-3 terrain roughness parameters for one category."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    z0_m: float = Field(gt=0, description="Roughness length (SANS 10160-3 Table 1).")
    zmin_m: float = Field(gt=0, description="Minimum height (SANS 10160-3 Table 1).")


# Intentionally EMPTY. Fill from SANS 10160-3 Table 1 once the registered engineer supplies the
# values (z0, zmin per A/B/C/D). Until then the kernel must NOT invent them.
_SANS_TERRAIN: dict[TerrainCategory, TerrainParameters] = {}


def sans_terrain_parameters(category: TerrainCategory) -> TerrainParameters:
    """Return SANS 10160-3 terrain parameters for a category, or raise if still PENDING."""
    try:
        return _SANS_TERRAIN[category]
    except KeyError:
        raise NotImplementedError(
            f"SANS 10160-3 terrain parameters (z0, zmin) for category {category.value} are PENDING "
            "— the registered engineer must supply SANS 10160-3 Table 1 values (see SOURCES.md E7). "
            "The kernel will not fabricate them."
        ) from None
