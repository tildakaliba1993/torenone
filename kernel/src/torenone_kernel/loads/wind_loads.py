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

from torenone_kernel.loads.wind import air_density, peak_velocity_pressure_kpa, peak_wind_speed
from torenone_kernel.loads.wind_pressure import (
    dominant_opening_internal_pressure,
    duopitch_roof_pressure_coefficients,
    enclosed_internal_pressure,
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
