"""Load computation modules. Characteristic loads only; SANS partial factors are applied at the
combination stage (Task 1.7)."""

from torenone_kernel.loads.combinations import load_combinations
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
from torenone_kernel.loads.wind_loads import wind_loads
from torenone_kernel.loads.wind_pressure import (
    InternalPressureCoefficients,
    RoofPressureCoefficients,
    WallPressureCoefficients,
    dominant_opening_internal_pressure,
    duopitch_roof_pressure_coefficients,
    enclosed_internal_pressure,
    wall_pressure_coefficients,
)

# WindLoadCase / WindLoadResult live in the models layer (results.py) to avoid a
# loads -> models -> loads import cycle; re-exported here for the public loads API.
from torenone_kernel.models.results import WindLoadCase, WindLoadResult

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
    # wind external pressure coefficients
    "wall_pressure_coefficients",
    "WallPressureCoefficients",
    "duopitch_roof_pressure_coefficients",
    "RoofPressureCoefficients",
    # wind internal pressure coefficients
    "enclosed_internal_pressure",
    "dominant_opening_internal_pressure",
    "InternalPressureCoefficients",
    # wind frame load assembly
    "wind_loads",
    "WindLoadResult",
    "WindLoadCase",
    # load combinations (SANS 10160-1)
    "load_combinations",
]
