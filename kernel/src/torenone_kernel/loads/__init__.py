"""Load computation modules. Characteristic loads only; SANS partial factors are applied at the
combination stage (Task 1.7)."""

from torenone_kernel.loads.dead import GRAVITY_M_S2, dead_loads
from torenone_kernel.loads.imposed import INACCESSIBLE_ROOF_QK_KPA, imposed_roof_loads
from torenone_kernel.loads.wind import (
    SA_BASIC_WIND_SPEED_ZONES_MS,
    TERRAIN_PARAMETERS,
    TerrainParameters,
    air_density,
    peak_velocity_pressure_kpa,
    peak_wind_speed,
    roughness_factor,
)

__all__ = [
    # dead
    "dead_loads",
    "GRAVITY_M_S2",
    # imposed
    "imposed_roof_loads",
    "INACCESSIBLE_ROOF_QK_KPA",
    # wind (SANS 10160-3:2019)
    "roughness_factor",
    "peak_wind_speed",
    "peak_velocity_pressure_kpa",
    "air_density",
    "TERRAIN_PARAMETERS",
    "TerrainParameters",
    "SA_BASIC_WIND_SPEED_ZONES_MS",
]
