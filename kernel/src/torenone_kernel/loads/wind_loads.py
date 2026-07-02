"""Assemble wind components into frame line loads — SANS 10160-3:2019 (PRD FR-7, Task 1.6d).

Ties together the velocity/pressure engine (qp) and the external/internal pressure coefficients
into net member line loads for the portal frame, transverse wind (θ = 0°):

    net pressure on a surface = qp · (cpe − cpi)      (positive = pressure onto the surface;
                                                       negative = suction / uplift)
    member UDL = net pressure × tributary width (bay spacing)

Load cases enumerate each cpi case × each windward-roof branch (suction/uplift vs pressure/
downforce); the downstream analysis takes the worst per member.

Assumptions (surfaced in the report's assumptions block, FR-27):
  - Reference height ze = apex (ridge) height — the building's highest point; also conservative
    (higher qp). Uniform pressure profile over the height (low-rise, h ≤ b).
  - h/d uses h = ze, d = span (transverse wind).
  - Internal-frame zones (walls D/E, roof H/I). Gable-edge zones and near-flat roofs deferred.
"""

from __future__ import annotations

from typing import NamedTuple

from torenone_kernel.loads.wind import air_density, peak_velocity_pressure_kpa, peak_wind_speed
from torenone_kernel.loads.wind_pressure import (
    dominant_opening_internal_pressure,
    duopitch_roof_pressure_coefficients,
    enclosed_internal_pressure,
    monopitch_roof_pressure_coefficients,
    wall_pressure_coefficients,
)
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import WindLoadCase, WindLoadResult


def wind_loads(spec: FrameSpec) -> WindLoadResult:
    """Compute the wind load cases (member UDLs) for the frame, transverse wind (θ = 0°)."""
    g = spec.geometry
    w = spec.wind

    ze = g.apex_height_m
    vp = peak_wind_speed(ze, w.terrain_category, w.basic_wind_speed_ms)
    qp = peak_velocity_pressure_kpa(vp, air_density(w.site_altitude_m))
    tributary_m = g.bay_spacing_m

    walls = wall_pressure_coefficients(ze / g.span_m)
    roof = duopitch_roof_pressure_coefficients(g.roof_pitch_deg)

    if w.has_dominant_opening:
        # Worst case for uplift: dominant opening on the windward wall (cpe at opening = zone D).
        internal = dominant_opening_internal_pressure(walls.cpe_windward)
    else:
        internal = enclosed_internal_pressure()

    roof_branches = (
        ("roof suction (uplift)", roof.windward_cpe_suction),
        ("roof pressure (downforce)", roof.windward_cpe_pressure),
    )

    cases: list[WindLoadCase] = []
    for cpi in internal.cpi_cases:
        for branch_name, cpe_roof_windward in roof_branches:
            ncp_ww = walls.cpe_windward - cpi
            ncp_lw = walls.cpe_leeward - cpi
            ncp_rw = cpe_roof_windward - cpi
            ncp_rl = roof.leeward_cpe_suction - cpi
            cases.append(
                WindLoadCase(
                    name=f"cpi={cpi:+.2f}, {branch_name}",
                    cpi=cpi,
                    net_cp_windward_wall=ncp_ww,
                    net_cp_leeward_wall=ncp_lw,
                    net_cp_windward_roof=ncp_rw,
                    net_cp_leeward_roof=ncp_rl,
                    windward_column_udl_kn_per_m=qp * ncp_ww * tributary_m,
                    leeward_column_udl_kn_per_m=qp * ncp_lw * tributary_m,
                    windward_rafter_udl_kn_per_m=qp * ncp_rw * tributary_m,
                    leeward_rafter_udl_kn_per_m=qp * ncp_rl * tributary_m,
                )
            )

    return WindLoadResult(
        peak_velocity_pressure_kpa=qp,
        reference_height_m=ze,
        scenario=internal.scenario,
        cases=tuple(cases),
        clause="SANS 10160-3:2019 cl. 7–8 — net = qp·(cpe − cpi)",
    )


def multispan_wind_loads(spec: FrameSpec) -> WindLoadResult:
    """Wind load cases for a MULTI-SPAN (duopitch) frame, transverse wind — SANS 10160-3:2019.

    PROVISIONAL (D13 wind). A multi-span roof is duopitch per span; equal spans are left-right
    symmetric, so one wind direction suffices. Reuses :class:`WindLoadCase` (windward wall →
    external column C0, leeward wall → Cn, windward slope → every ``RL{s}``, leeward slope →
    every ``RR{s}``). Differences from the single-span :func:`wind_loads`:
      * ``h/d`` uses the FULL building width across all spans (the wind's fetch), not one span;
      * the SAME duopitch zone-H/I coefficients are applied to EVERY span — this ignores the
        code's reduction on downwind spans (cl. 8.3.6), so it is CONSERVATIVE and simple.
    """
    g = spec.geometry
    w = spec.wind

    ze = g.apex_height_m
    vp = peak_wind_speed(ze, w.terrain_category, w.basic_wind_speed_ms)
    qp = peak_velocity_pressure_kpa(vp, air_density(w.site_altitude_m))
    tributary_m = g.bay_spacing_m

    walls = wall_pressure_coefficients(ze / g.building_width_m)  # d = full width across spans
    roof = duopitch_roof_pressure_coefficients(g.roof_pitch_deg)

    if w.has_dominant_opening:
        internal = dominant_opening_internal_pressure(walls.cpe_windward)
    else:
        internal = enclosed_internal_pressure()

    roof_branches = (
        ("roof suction (uplift)", roof.windward_cpe_suction),
        ("roof pressure (downforce)", roof.windward_cpe_pressure),
    )

    cases: list[WindLoadCase] = []
    for cpi in internal.cpi_cases:
        for branch_name, cpe_roof_windward in roof_branches:
            ncp_ww = walls.cpe_windward - cpi
            ncp_lw = walls.cpe_leeward - cpi
            ncp_rw = cpe_roof_windward - cpi
            ncp_rl = roof.leeward_cpe_suction - cpi
            cases.append(
                WindLoadCase(
                    name=f"cpi={cpi:+.2f}, {branch_name}",
                    cpi=cpi,
                    net_cp_windward_wall=ncp_ww,
                    net_cp_leeward_wall=ncp_lw,
                    net_cp_windward_roof=ncp_rw,
                    net_cp_leeward_roof=ncp_rl,
                    windward_column_udl_kn_per_m=qp * ncp_ww * tributary_m,
                    leeward_column_udl_kn_per_m=qp * ncp_lw * tributary_m,
                    windward_rafter_udl_kn_per_m=qp * ncp_rw * tributary_m,
                    leeward_rafter_udl_kn_per_m=qp * ncp_rl * tributary_m,
                )
            )

    return WindLoadResult(
        peak_velocity_pressure_kpa=qp,
        reference_height_m=ze,
        scenario=internal.scenario,
        cases=tuple(cases),
        clause="SANS 10160-3:2019 cl. 7–8 (multi-span, duopitch per span) — net = qp·(cpe − cpi)",
    )


class MonopitchWindCase(NamedTuple):
    """One mono-pitch wind load case: per-member UDLs + the net coefficients used.

    UDL sign conventions match :meth:`MonopitchAnalysis._build_wind_model`: column UDLs +ve =
    pressure (resolved to the correct inward/outward direction per column in the model); rafter
    UDL +ve = pressure onto the roof, −ve = uplift.
    """

    name: str
    cpi: float
    net_cp_low_wall: float
    net_cp_high_wall: float
    net_cp_roof: float
    low_column_udl_kn_per_m: float
    high_column_udl_kn_per_m: float
    rafter_udl_kn_per_m: float


class MonopitchWindResult(NamedTuple):
    """Characteristic mono-pitch wind actions (SANS 10160-3): qp + per-case per-member loads."""

    peak_velocity_pressure_kpa: float
    reference_height_m: float
    scenario: str
    cases: tuple[MonopitchWindCase, ...]
    clause: str


def monopitch_wind_loads(spec: FrameSpec) -> MonopitchWindResult:
    """Mono-pitch wind load cases (per-member UDLs), transverse wind — SANS 10160-3:2019.

    PROVISIONAL (D12 wind). A mono-pitch is asymmetric, so BOTH transverse directions are
    enumerated: θ=0° (wind up the slope — low wall windward, two roof branches per Table 8 NOTE 1)
    and θ=180° (wind over the high side — high wall windward, roof in suction). Each is crossed with
    every internal-pressure (cpi) case; the downstream analysis takes the worst per member.
    """
    g = spec.geometry
    w = spec.wind

    ze = g.high_eaves_height_m  # highest point of the single-slope roof
    vp = peak_wind_speed(ze, w.terrain_category, w.basic_wind_speed_ms)
    qp = peak_velocity_pressure_kpa(vp, air_density(w.site_altitude_m))
    tributary_m = g.bay_spacing_m

    walls = wall_pressure_coefficients(ze / g.span_m)
    roof = monopitch_roof_pressure_coefficients(g.roof_pitch_deg)

    if w.has_dominant_opening:
        internal = dominant_opening_internal_pressure(walls.cpe_windward)
    else:
        internal = enclosed_internal_pressure()

    cases: list[MonopitchWindCase] = []
    for cpi in internal.cpi_cases:
        # θ=0°: wind up the slope. Low wall = windward (D), high wall = leeward (E). Two roof branches.
        for branch, cpe_roof in (
            ("θ=0° roof suction (uplift)", roof.theta0_cpe_suction),
            ("θ=0° roof pressure (downforce)", roof.theta0_cpe_pressure),
        ):
            ncp_low = walls.cpe_windward - cpi
            ncp_high = walls.cpe_leeward - cpi
            ncp_roof = cpe_roof - cpi
            cases.append(
                MonopitchWindCase(
                    name=f"cpi={cpi:+.2f}, {branch}",
                    cpi=cpi,
                    net_cp_low_wall=ncp_low,
                    net_cp_high_wall=ncp_high,
                    net_cp_roof=ncp_roof,
                    low_column_udl_kn_per_m=qp * ncp_low * tributary_m,
                    high_column_udl_kn_per_m=qp * ncp_high * tributary_m,
                    rafter_udl_kn_per_m=qp * ncp_roof * tributary_m,
                )
            )
        # θ=180°: wind over the high side. High wall = windward (D), low wall = leeward (E); roof suction.
        ncp_low = walls.cpe_leeward - cpi
        ncp_high = walls.cpe_windward - cpi
        ncp_roof = roof.theta180_cpe_suction - cpi
        cases.append(
            MonopitchWindCase(
                name=f"cpi={cpi:+.2f}, θ=180° roof suction (uplift)",
                cpi=cpi,
                net_cp_low_wall=ncp_low,
                net_cp_high_wall=ncp_high,
                net_cp_roof=ncp_roof,
                low_column_udl_kn_per_m=qp * ncp_low * tributary_m,
                high_column_udl_kn_per_m=qp * ncp_high * tributary_m,
                rafter_udl_kn_per_m=qp * ncp_roof * tributary_m,
            )
        )

    return MonopitchWindResult(
        peak_velocity_pressure_kpa=qp,
        reference_height_m=ze,
        scenario=internal.scenario,
        cases=tuple(cases),
        clause="SANS 10160-3:2019 cl. 7–8 (mono-pitch, Table 8) — net = qp·(cpe − cpi)",
    )
