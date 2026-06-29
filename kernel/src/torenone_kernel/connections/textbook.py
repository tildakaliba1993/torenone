"""Connection mechanics transcribed from the Mahachi textbook (CSIR 2004), Chapter 7.

⚠️ PROVISIONAL — transcribed from an **accredited published SA source** (Mahachi, *Design of
Structural Steelwork to SANS 10162*, §7.6 / §7.5.1), worked Examples **E7.5–E7.9**. Each routine
reproduces that book's published answers (proven in
``kernel/tests/validation/textbook/test_textbook_connections.py``).

Two methods, both second-authority benchmarks for our connection design:

1. **Elastic bolt-group analysis** (eq. 7.27) — a bolt group loaded *in its own plane* by direct
   shear + an in-plane moment (brackets, splices, side-plate connections). The force on the
   most-stressed bolt is the vector sum of the direct share `V/n` and the moment share `M·r/J`
   (J = Σ(x²+y²)). Reproduces E7.6 (web splice), E7.7 (eccentric bracket), E7.9 (side plates).

2. **Eurocode-3 T-stub prying** (§7.5.1 / E7.5) — the bolt tension *including prying action* for a
   T-stub / end-plate flange in bending. This is the check our portal end-plate
   (``connections/moment_endplate.py``) currently OMITS (it flags prying as not modelled), so this
   is the published method to close that gap. NOT yet wired into the live end-plate design — awaits
   registered-engineer sign-off (see docs/REDBOOK-VALIDATION.md).

The bolt-group method is for *in-plane* bracket/splice connections, which the single-bay portal MVP
does not currently design (its eaves/apex are out-of-plane end-plate moment connections). It is
included as a validated primitive + second-authority confirmation of the bolt mechanics.
"""

from __future__ import annotations

import dataclasses
import math


# --------------------------------------------------------------------------------------------
# 1. Elastic bolt-group analysis (eq. 7.27) — E7.6 / E7.7 / E7.9
# --------------------------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class BoltGroupResult:
    """Resultant force on the most-stressed bolt of an in-plane-loaded bolt group."""

    polar_inertia_mm2: float        # J = Σ(xᵢ² + yᵢ²)
    direct_fx_kn: float             # Vx / n
    direct_fy_kn: float             # Vy / n
    moment_force_kn: float          # |M·r/J| on the critical bolt
    resultant_kn: float             # vector sum on the most-stressed bolt
    critical_bolt: tuple[float, float]


def bolt_group_resultant(
    bolts: list[tuple[float, float]],
    *,
    shear_x_kn: float,
    shear_y_kn: float,
    in_plane_moment_knm: float,
) -> BoltGroupResult:
    """Resultant force on the most-stressed bolt (elastic / instantaneous-centre method, eq. 7.27).

    Bolt coordinates ``(x, y)`` are measured from the group centroid (mm). The direct load is
    shared equally (``V/n``); the in-plane moment adds, on each bolt, a force ``M·r/J`` perpendicular
    to its radius (components ``(M·y/J, −M·x/J)``). The function returns the largest resultant over
    all bolts (sign-robust for symmetric groups).
    """
    n = len(bolts)
    j = sum(x * x + y * y for x, y in bolts)
    fxd = shear_x_kn / n
    fyd = shear_y_kn / n
    m_knmm = in_plane_moment_knm * 1_000.0          # kN·m → kN·mm

    best: BoltGroupResult | None = None
    for x, y in bolts:
        fxm = m_knmm * y / j                          # kN  (kN·mm · mm / mm²)
        fym = -m_knmm * x / j
        resultant = math.hypot(fxd + fxm, fyd + fym)
        if best is None or resultant > best.resultant_kn:
            best = BoltGroupResult(
                polar_inertia_mm2=j,
                direct_fx_kn=fxd,
                direct_fy_kn=fyd,
                moment_force_kn=math.hypot(fxm, fym),
                resultant_kn=resultant,
                critical_bolt=(x, y),
            )
    assert best is not None  # bolt list is non-empty
    return best


# --------------------------------------------------------------------------------------------
# 2. Eurocode-3 T-stub prying (§7.5.1 / E7.5)
# --------------------------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class PryingResult:
    """Bolt tension including prying action for a T-stub / end-plate flange (EC3, E7.5)."""

    m_mm: float                     # bolt line → web/root (with the 0.8·r allowance)
    e_mm: float                     # edge distance
    n_mm: float                     # prying lever (≤ 1.25·m)
    sum_l_eff_mm: float             # Σ effective length (yield-line)
    moment_resistance_nmm: float    # Mr of the T-stub flange
    bolt_tension_kn: float          # Tu per bolt, including prying
    prying_increase_pct: float      # Tu vs the no-prying value P/N


def tstub_prying_bolt_tension(
    *,
    applied_force_kn: float,        # Pu — total tension on the T-stub (one flange)
    n_bolts: int,                   # N — bolts in the T-stub
    gauge_mm: float,                # bolt cross-centre (across the web)
    flange_width_mm: float,         # bf
    flange_thickness_mm: float,     # tf
    web_thickness_mm: float,        # tw (the value the example subtracts)
    root_radius_mm: float,          # r — the EC3 0.8·r allowance to the yield line
    bolt_pitch_mm: float,           # p — along the flange
    end_distance_mm: float,         # physical end distance limiting s
    fy_mpa: float = 300.0,
    phi_plate: float = 0.90,
) -> PryingResult:
    """T-stub bolt tension including prying action, per Eurocode 3 (book §7.5.1, Example E7.5).

    Steps: geometry (m, e, n) → yield-line effective length Σl_eff → flange moment resistance Mr
    → bolt tension Tu. For the EC3 mode where ``Mr > 0.25·m·Pu`` (prying present, flange not fully
    plastic): ``Tu = ((m + n)·Pu − 2·Mr) / (n·N)``.
    """
    m = (gauge_mm - 2.0 * 0.8 * root_radius_mm - web_thickness_mm) / 2.0
    e = (flange_width_mm - gauge_mm) / 2.0
    e_min = e
    n = min(e_min, 1.25 * m)

    # Yield-line effective length (circular vs side patterns), capped at the physical end distance.
    s = min(2.0 * m + 0.625 * e, math.pi * m, end_distance_mm)
    l_eff_a = min(bolt_pitch_mm / 2.0 + s, 2.0 * s)
    sum_l_eff = 2.0 * l_eff_a

    mr_nmm = 0.25 * phi_plate * sum_l_eff * flange_thickness_mm**2 * fy_mpa

    pu_n = applied_force_kn * 1_000.0               # N
    # EC3 prying force (mode 2): flange yields, prying present.
    tu_n = ((m + n) * pu_n - 2.0 * mr_nmm) / (n * n_bolts)
    tu_kn = tu_n / 1_000.0

    no_prying_kn = applied_force_kn / n_bolts
    increase_pct = (tu_kn - no_prying_kn) / no_prying_kn * 100.0

    return PryingResult(
        m_mm=m,
        e_mm=e,
        n_mm=n,
        sum_l_eff_mm=sum_l_eff,
        moment_resistance_nmm=mr_nmm,
        bolt_tension_kn=tu_kn,
        prying_increase_pct=increase_pct,
    )
