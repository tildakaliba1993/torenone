"""Load computation modules. Characteristic loads only; SANS partial factors are applied at the
combination stage (Task 1.7)."""

from torenone_kernel.loads.dead import GRAVITY_M_S2, dead_loads
from torenone_kernel.loads.imposed import INACCESSIBLE_ROOF_QK_KPA, imposed_roof_loads

__all__ = [
    "dead_loads",
    "GRAVITY_M_S2",
    "imposed_roof_loads",
    "INACCESSIBLE_ROOF_QK_KPA",
]
