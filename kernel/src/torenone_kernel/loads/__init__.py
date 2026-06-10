"""Load computation modules. Characteristic loads only; SANS partial factors are applied at the
combination stage (Task 1.7)."""

from torenone_kernel.loads.dead import GRAVITY_M_S2, dead_loads

__all__ = ["dead_loads", "GRAVITY_M_S2"]
