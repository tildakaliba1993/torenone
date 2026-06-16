"""BMD/SFD + stick-model sampling (FR-32) — the structured data behind the diagrams.

Builds and solves the portal-frame PyNite model for the governing **ULS-1** combination
on the *final* sections, then samples bending moment, shear and axial force at evenly
spaced stations along each of the four members. Returns a :class:`FrameDiagram` — the
single source of truth shared by:

  * :func:`design`/:func:`check` — attached to ``DesignResult.diagram`` for the web UI;
  * the PDF report (``report.diagrams.bmd_sfd_png`` renders from this same data).

Depends only on PyNite + the kernel loads (no matplotlib), so the core design path does
not pull a report-only dependency.

No arithmetic on the force values lives here — every M/V/N comes straight from the
PyNite analysis (units converted: N·mm → kN·m, N → kN).
"""

from __future__ import annotations

import math
from typing import Any

from torenone_kernel.loads.combinations import load_combinations
from torenone_kernel.loads.dead import dead_loads
from torenone_kernel.loads.imposed import imposed_roof_loads
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import (
    DiagramStation,
    FrameDiagram,
    LoadCombination,
    MemberDiagram,
)
from torenone_kernel.sections.properties import SectionProperties

# Sample points per member for the BMD/SFD curves (matches the PDF diagram resolution).
N_STATIONS = 50

# Material constants (SANS 10162-1 cl. 3.2 — VERIFIED) + PyNite model bookkeeping.
_E = 200_000.0      # N/mm²
_G = 77_000.0       # N/mm²
_NU = 0.3
_RHO = 7.85e-9      # tonne/mm³ (self-weight not applied here; UDLs carry the loads)
_COMBO_INTERNAL = "LC"


def _combo_starting_with(combos: dict[str, LoadCombination], prefix: str) -> LoadCombination:
    for name, combo in combos.items():
        if name.startswith(prefix):
            return combo
    raise KeyError(f"No load combination starting with {prefix!r}")


def build_frame_model(
    spec: FrameSpec,
    col_sec: SectionProperties,
    raf_sec: SectionProperties,
    uls_rafter_udl: float,
    uls_col_axial: float,
) -> tuple[Any, str]:
    """Build + solve the portal PyNite model under the given ULS-1 UDLs.

    Returns ``(model, combo_name)`` so callers can sample member forces. Mirrors
    :meth:`PortalAnalysis.run` so the diagram agrees with the design analysis.
    """
    import site as _site
    import sys as _sys

    for _sp in _site.getsitepackages() + [_site.getusersitepackages()]:
        if _sp not in _sys.path:
            _sys.path.insert(0, _sp)

    from Pynite import FEModel3D

    g = spec.geometry
    span_mm = g.span_m * 1_000.0
    eaves_h_mm = g.eaves_height_m * 1_000.0
    apex_h_mm = g.apex_height_m * 1_000.0
    half_span_mm = span_mm / 2.0

    m = FEModel3D()
    m.add_material("steel", _E, _G, _NU, _RHO)

    def _add_sec(name: str, sec: SectionProperties) -> None:
        m.add_section(name, A=sec.area_mm2, Iy=sec.second_moment_iy_mm4,
                      Iz=sec.second_moment_ix_mm4, J=sec.torsion_constant_j_mm4)

    _add_sec("col_sec", col_sec)
    _add_sec("raf_sec", raf_sec)

    m.add_node("BL", 0, 0, 0)
    m.add_node("EL", 0, eaves_h_mm, 0)
    m.add_node("AP", half_span_mm, apex_h_mm, 0)
    m.add_node("ER", span_mm, eaves_h_mm, 0)
    m.add_node("BR", span_mm, 0, 0)

    def _pin(node: str) -> None:
        m.def_support(node, True, True, True, True, True, False)

    def _oop(node: str) -> None:
        m.def_support(node, False, False, True, True, True, False)

    _pin("BL")
    _pin("BR")
    _oop("EL")
    _oop("AP")
    _oop("ER")

    m.add_member("COL_L", "BL", "EL", "steel", "col_sec")
    m.add_member("RAF_L", "EL", "AP", "steel", "raf_sec")
    m.add_member("RAF_R", "AP", "ER", "steel", "raf_sec")
    m.add_member("COL_R", "ER", "BR", "steel", "col_sec")

    if uls_rafter_udl != 0.0:
        m.add_member_dist_load("RAF_L", "Fy", -uls_rafter_udl, -uls_rafter_udl, case="DL")
        m.add_member_dist_load("RAF_R", "Fy", -uls_rafter_udl, -uls_rafter_udl, case="DL")
    if uls_col_axial != 0.0:
        m.add_member_dist_load("COL_L", "Fy", -uls_col_axial, -uls_col_axial, case="DL")
        m.add_member_dist_load("COL_R", "Fy", -uls_col_axial, -uls_col_axial, case="DL")

    m.add_load_combo(_COMBO_INTERNAL, {"DL": 1.0})
    m.analyze_linear(log=False, check_stability=False)
    return m, _COMBO_INTERNAL


# Member layout: (pynite name, label, which-section, start-node, end-node).
_MEMBERS = [
    ("column_left", "Col L", "column", "BL", "EL", "COL_L"),
    ("rafter_left", "Rafter L", "rafter", "EL", "AP", "RAF_L"),
    ("rafter_right", "Rafter R", "rafter", "AP", "ER", "RAF_R"),
    ("column_right", "Col R", "column", "ER", "BR", "COL_R"),
]


def _frame_nodes(spec: FrameSpec) -> dict[str, tuple[float, float]]:
    g = spec.geometry
    return {
        "BL": (0.0, 0.0),
        "EL": (0.0, g.eaves_height_m),
        "AP": (g.span_m / 2.0, g.apex_height_m),
        "ER": (g.span_m, g.eaves_height_m),
        "BR": (g.span_m, 0.0),
    }


def compute_frame_diagram(
    spec: FrameSpec,
    col_sec: SectionProperties,
    raf_sec: SectionProperties,
) -> FrameDiagram:
    """Sample the governing ULS-1 BMD/SFD/axial for *spec* on the final sections."""
    # Reconstruct the governing ULS-1 factored UDLs (same logic as design.py / the PDF).
    combos_list = load_combinations(spec)
    combos = {c.name.split()[0]: c for c in combos_list}
    uls1 = _combo_starting_with(combos, "ULS-1")
    gamma_g = uls1.factors["dead"]
    gamma_q = uls1.factors.get("imposed", 0.0)

    dead = dead_loads(spec, rafter=raf_sec, column=col_sec)
    imposed = imposed_roof_loads(spec)
    uls_rafter_udl = gamma_g * dead.rafter_udl_kn_per_m + gamma_q * imposed.roof_udl_kn_per_m
    uls_col_axial = gamma_g * (dead.column_self_weight_kn_per_m + dead.wall_cladding_udl_kn_per_m)

    model, combo = build_frame_model(spec, col_sec, raf_sec, uls_rafter_udl, uls_col_axial)

    nodes = _frame_nodes(spec)
    g = spec.geometry
    eaves_h_mm = g.eaves_height_m * 1_000.0
    rafter_len_mm = math.hypot(
        g.span_m / 2.0 * 1_000.0, (g.apex_height_m - g.eaves_height_m) * 1_000.0
    )
    length_mm = {"column": eaves_h_mm, "rafter": rafter_len_mm}

    members: list[MemberDiagram] = []
    max_m = 0.0
    max_v = 0.0
    for name, label, section, ni, nj, pynite_name in _MEMBERS:
        L_mm = length_mm[section]
        start = nodes[ni]
        end = nodes[nj]
        member = model.members[pynite_name]
        stations: list[DiagramStation] = []
        for k in range(N_STATIONS):
            t = k / (N_STATIONS - 1)
            x_mm = t * L_mm
            moment = member.moment("Mz", x_mm, combo) / 1_000_000.0   # N·mm → kN·m
            shear = member.shear("Fy", x_mm, combo) / 1_000.0         # N → kN
            axial = member.axial(x_mm, combo) / 1_000.0               # N → kN
            stations.append(
                DiagramStation(
                    pos_m=x_mm / 1_000.0,
                    x_m=start[0] + t * (end[0] - start[0]),
                    y_m=start[1] + t * (end[1] - start[1]),
                    axial_kn=axial,
                    shear_kn=shear,
                    moment_knm=moment,
                )
            )
            max_m = max(max_m, abs(moment))
            max_v = max(max_v, abs(shear))
        members.append(
            MemberDiagram(
                name=name, label=label, member=section,
                start=start, end=end, length_m=L_mm / 1_000.0, stations=stations,
            )
        )

    return FrameDiagram(
        combination=uls1.name,
        nodes=nodes,
        members=members,
        max_abs_moment_knm=max_m,
        max_abs_shear_kn=max_v,
    )
