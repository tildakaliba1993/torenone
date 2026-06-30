"""Plane-frame analysis engine — Task 1.8.

Thin wrapper around PyNite (PyNiteFEA) for first-order linear-elastic 2-D analysis.

Unit convention (internal, passed to PyNite):
    Length : mm
    Force  : N
    Stress : N/mm² (MPa)
    Moment : N·mm

All public helpers accept and return these units EXCEPT PortalAnalysis.run(), which accepts
loads in kN/m and returns forces in kN / kN·m (to match the AnalysisResult contract).

Material constants (steel, first-order elastic):
    E = 200 000 N/mm²   (SANS 10162-1:2011 cl. 5.2 — to be confirmed at Task 1.10)
    G =  77 000 N/mm²   (standard value; ν ≈ 0.3 → G = E/2(1+ν) = 76 923 ≈ 77 000)

PyNite coordinate convention used here:
    X = horizontal (along span)
    Y = vertical (up)
    Z = out-of-plane (constrained to keep the model 2-D)

Out-of-plane constraints: DZ, RX, RY restrained at every node so the 3-D solver behaves
as a plane-frame solver.
"""

from __future__ import annotations

import math

# PyNite is installed --user; ensure the user site-packages is on sys.path.
import site
import sys

for _sp in site.getsitepackages() + [site.getusersitepackages()]:
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from Pynite import FEModel3D

from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import AnalysisResult, MemberForces
from torenone_kernel.sections.properties import SectionProperties

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
_E_STEEL_MPA = 200_000.0   # N/mm²  — SANS 10162-1:2011 cl. 5.2 (PROVISIONAL — Task 1.10)
_G_STEEL_MPA =  77_000.0   # N/mm²
_NU_STEEL    =       0.3
_RHO_STEEL   =   7.85e-9   # N/mm³ (7 850 kg/m³) — self-weight not used here but required by PyNite

_COMBO = "LC"  # internal load-combo name used within every helper model


# ---------------------------------------------------------------------------
# Internal model-builder helpers
# ---------------------------------------------------------------------------

def _new_model() -> FEModel3D:
    m = FEModel3D()
    m.add_material("steel", _E_STEEL_MPA, _G_STEEL_MPA, _NU_STEEL, _RHO_STEEL)
    return m


def _add_section(model: FEModel3D, name: str, sec: SectionProperties) -> None:
    model.add_section(
        name,
        A=sec.area_mm2,
        Iy=sec.second_moment_iy_mm4,
        Iz=sec.second_moment_ix_mm4,   # major axis = Iz in PyNite (bending in X-Y plane)
        J=sec.torsion_constant_j_mm4,
    )


def _pin_support(model: FEModel3D, node: str) -> None:
    """2-D pinned support: restrains DX, DY, DZ, RX, RY (free RZ = rotation in plane)."""
    model.def_support(node, True, True, True, True, True, False)


def _fix_out_of_plane(model: FEModel3D, node: str) -> None:
    """Restrain DZ, RX, RY for an internal node to enforce 2-D behaviour."""
    model.def_support(node, False, False, True, True, True, False)


def _add_load_combo(model: FEModel3D, case: str = "DL") -> None:
    model.add_load_combo(_COMBO, {case: 1.0})


def _member_end_moment_Nmm(model: FEModel3D, member_name: str, x_mm: float) -> float:
    """Return Mz at position x_mm along member (N·mm, sign = PyNite convention)."""
    return float(model.members[member_name].moment("Mz", x_mm, _COMBO))


def _member_shear_N(model: FEModel3D, member_name: str, x_mm: float) -> float:
    return float(model.members[member_name].shear("Fy", x_mm, _COMBO))


def _reaction(model: FEModel3D, node: str, dof: str) -> float:
    """Extract a reaction force/moment from a solved model (N or N·mm)."""
    return float(model.nodes[node].__dict__[dof][_COMBO])


# ---------------------------------------------------------------------------
# Validation helpers — exact determinate cases
# ---------------------------------------------------------------------------

def solve_simple_beam_udl(
    w_n_per_mm: float,
    span_mm: float,
    section: SectionProperties,
) -> dict[str, float]:
    """Solve a simply-supported beam under uniform downward UDL (N/mm).

    Returns dict with keys:
        reaction_i_N, reaction_j_N — support reactions (upward positive)
        moment_mid_Nmm             — bending moment at mid-span (N·mm)
        shear_max_N                — |V| at support face (N)
    """
    m = _new_model()
    _add_section(m, "sec", section)
    m.add_node("N1", 0, 0, 0)
    m.add_node("N2", span_mm, 0, 0)
    # Simple supports: pin at N1 (DX+DY), roller at N2 (DY only); both restrain out-of-plane
    m.def_support("N1", True, True, True, True, True, False)
    m.def_support("N2", False, True, True, True, True, False)
    m.add_member("M1", "N1", "N2", "steel", "sec")
    m.add_member_dist_load("M1", "Fy", -w_n_per_mm, -w_n_per_mm, case="DL")
    _add_load_combo(m)
    m.analyze_linear(log=False, check_stability=False)

    ri = float(m.nodes["N1"].RxnFY[_COMBO])
    rj = float(m.nodes["N2"].RxnFY[_COMBO])
    m_mid = m.members["M1"].moment("Mz", span_mm / 2, _COMBO)
    v_max = abs(m.members["M1"].shear("Fy", 0.0, _COMBO))
    return {
        "reaction_i_N":   ri,
        "reaction_j_N":   rj,
        "moment_mid_Nmm": m_mid,
        "shear_max_N":    v_max,
    }


def solve_cantilever_point_load(
    P_n: float,
    length_mm: float,
    section: SectionProperties,
) -> dict[str, float]:
    """Solve a cantilever with point load P (N downward) at the free tip.

    Returns dict with keys:
        moment_fixed_Nmm — bending moment at the fixed end (N·mm, magnitude)
        shear_N          — shear force (N, magnitude)
    """
    m = _new_model()
    _add_section(m, "sec", section)
    m.add_node("N1", 0, 0, 0)
    m.add_node("N2", length_mm, 0, 0)
    # Fixed at N1, free at N2
    m.def_support("N1", True, True, True, True, True, True)
    # N2 is unsupported in-plane; restrain out-of-plane
    m.def_support("N2", False, False, True, True, True, False)
    m.add_member("M1", "N1", "N2", "steel", "sec")
    m.add_node_load("N2", "FY", -P_n, case="DL")
    _add_load_combo(m)
    m.analyze_linear(log=False, check_stability=False)

    m_fixed = abs(float(m.nodes["N1"].RxnMZ[_COMBO]))
    v = abs(float(m.nodes["N1"].RxnFY[_COMBO]))
    return {
        "moment_fixed_Nmm": m_fixed,
        "shear_N":          v,
    }


def solve_portal_udl(
    span_mm: float,
    height_mm: float,
    w_n_per_mm: float,
    section: SectionProperties,
) -> dict[str, float]:
    """Solve a pinned-base symmetric portal frame with flat (horizontal) rafter and
    vertical UDL w (N/mm) applied on the rafter.

    Nodes:
        BL — base left   (0, 0)
        EL — eaves left  (0, height_mm)
        ER — eaves right (span_mm, height_mm)
        BR — base right  (span_mm, 0)

    Returns dict with keys:
        H_N          — horizontal thrust at each base (N, equal by symmetry)
        V_N          — vertical reaction at each base (N, equal by symmetry)
        M_eaves_Nmm  — bending moment at eaves (N·mm, magnitude)
    """
    m = _new_model()
    _add_section(m, "sec", section)
    m.add_node("BL",        0,        0, 0)
    m.add_node("EL",        0, height_mm, 0)
    m.add_node("ER", span_mm, height_mm, 0)
    m.add_node("BR", span_mm,        0, 0)

    # Pinned bases
    _pin_support(m, "BL")
    _pin_support(m, "BR")
    # Interior nodes: restrain out-of-plane only
    _fix_out_of_plane(m, "EL")
    _fix_out_of_plane(m, "ER")

    m.add_member("CL", "BL", "EL", "steel", "sec")   # left column
    m.add_member("RF", "EL", "ER", "steel", "sec")   # rafter (flat)
    m.add_member("CR", "ER", "BR", "steel", "sec")   # right column

    m.add_member_dist_load("RF", "Fy", -w_n_per_mm, -w_n_per_mm, case="DL")
    _add_load_combo(m)
    m.analyze_linear(log=False, check_stability=False)

    H_N = abs(float(m.nodes["BL"].RxnFX[_COMBO]))
    V_N = abs(float(m.nodes["BL"].RxnFY[_COMBO]))
    M_eaves = abs(m.members["CL"].moment("Mz", height_mm, _COMBO))
    return {
        "H_N":         H_N,
        "V_N":         V_N,
        "M_eaves_Nmm": M_eaves,
    }


def solve_monopitch_udl(
    span_mm: float,
    eaves_low_mm: float,
    eaves_high_mm: float,
    w_n_per_mm: float,
    col_section: SectionProperties,
    raf_section: SectionProperties,
) -> dict[str, float]:
    """Solve a pinned-base **mono-pitch** (single-slope) portal frame under a vertical UDL.

    PROVISIONAL — new geometry (T1-3), pending registered-engineer validation. The model is the
    asymmetric analogue of :func:`solve_portal_udl`: a low column, a single sloping rafter, and a
    high column. ``w_n_per_mm`` is applied as a global vertical (Fy) load per unit rafter length.

    Nodes:
        BL — base, low side   (0, 0)
        EL — eaves, low side  (0, eaves_low_mm)
        EH — eaves, high side (span_mm, eaves_high_mm)
        BH — base, high side  (span_mm, 0)

    Returns a dict of signed reactions (N) and salient moments (N·mm), plus the total applied
    vertical load — enough to verify global equilibrium and the pinned-base conditions.
    """
    raf_len_mm = math.hypot(span_mm, eaves_high_mm - eaves_low_mm)

    m = _new_model()
    _add_section(m, "col_sec", col_section)
    _add_section(m, "raf_sec", raf_section)
    m.add_node("BL",       0,            0, 0)
    m.add_node("EL",       0,  eaves_low_mm, 0)
    m.add_node("EH", span_mm, eaves_high_mm, 0)
    m.add_node("BH", span_mm,            0, 0)

    _pin_support(m, "BL")
    _pin_support(m, "BH")
    _fix_out_of_plane(m, "EL")
    _fix_out_of_plane(m, "EH")

    m.add_member("COL_L", "BL", "EL", "steel", "col_sec")   # low column  (i=base, j=eaves)
    m.add_member("RAF",   "EL", "EH", "steel", "raf_sec")   # single sloping rafter
    m.add_member("COL_H", "EH", "BH", "steel", "col_sec")   # high column (i=eaves, j=base)

    # Gravity is a GLOBAL vertical load ("FY", uppercase) — not the member-local perpendicular
    # ("Fy"). w is per unit rafter length, so the total vertical = w x rafter length.
    m.add_member_dist_load("RAF", "FY", -w_n_per_mm, -w_n_per_mm, case="DL")
    _add_load_combo(m)
    m.analyze_linear(log=False, check_stability=False)

    return {
        "V_low_N":          float(m.nodes["BL"].RxnFY[_COMBO]),
        "V_high_N":         float(m.nodes["BH"].RxnFY[_COMBO]),
        "H_low_N":          float(m.nodes["BL"].RxnFX[_COMBO]),
        "H_high_N":         float(m.nodes["BH"].RxnFX[_COMBO]),
        # COL_L runs base(x=0) -> eaves(x=eaves_low); COL_H runs eaves(x=0) -> base(x=eaves_high).
        "M_eaves_low_Nmm":  abs(m.members["COL_L"].moment("Mz", eaves_low_mm,  _COMBO)),
        "M_eaves_high_Nmm": abs(m.members["COL_H"].moment("Mz", 0.0, _COMBO)),
        "M_base_low_Nmm":   abs(m.members["COL_L"].moment("Mz", 0.0, _COMBO)),
        "M_base_high_Nmm":  abs(m.members["COL_H"].moment("Mz", eaves_high_mm, _COMBO)),
        "total_vertical_N": w_n_per_mm * raf_len_mm,
    }


# ---------------------------------------------------------------------------
# Portal builder from FrameSpec
# ---------------------------------------------------------------------------

class PortalAnalysis:
    """Build a pinned-base pitched portal frame model from FrameSpec and section properties,
    apply loads, and return an AnalysisResult.

    Geometry (all in mm):
        BL  — column base, left   (0, 0)
        EL  — eaves, left         (0, eaves_h)
        AP  — apex               (half_span, apex_h)
        ER  — eaves, right        (span, eaves_h)
        BR  — column base, right  (span, 0)

    Members:
        COL_L  BL → EL  (column)
        RAF_L  EL → AP  (left rafter half)
        RAF_R  AP → ER  (right rafter half)
        COL_R  ER → BR  (column)

    Loads are applied in the global Y-direction (vertical). The caller converts kN/m to N/mm.
    For inclined rafters, the UDL is applied as a global Fy load (vertical projection), which
    is the standard approach for gravity loads.
    """

    def __init__(
        self,
        spec: FrameSpec,
        column_section: SectionProperties,
        rafter_section: SectionProperties,
    ) -> None:
        self.spec = spec
        self.col_sec = column_section
        self.raf_sec = rafter_section

    def run(
        self,
        combination_name: str,
        rafter_udl_kn_per_m: float,
        column_axial_kn_per_m: float = 0.0,
    ) -> AnalysisResult:
        """Analyse one load combination.

        Parameters
        ----------
        combination_name : label for the AnalysisResult.
        rafter_udl_kn_per_m : vertical UDL on each rafter (kN/m, downward = positive).
        column_axial_kn_per_m : vertical UDL on columns, e.g. cladding (kN/m, downward +).

        Returns
        -------
        AnalysisResult with MemberForces at: col_base_L, eaves_L, apex, eaves_R, col_base_R.
        """
        geom = self.spec.geometry
        span_mm      = geom.span_m      * 1_000.0
        eaves_h_mm   = geom.eaves_height_m * 1_000.0
        apex_h_mm    = geom.apex_height_m  * 1_000.0
        half_span_mm = span_mm / 2.0

        # Rafter half-length (along member local x)
        rafter_len_mm = math.hypot(half_span_mm, apex_h_mm - eaves_h_mm)

        # Convert loads: kN/m → N/mm
        w_raf_n_mm = rafter_udl_kn_per_m   # kN/m = N/mm  (same numeric value!)
        w_col_n_mm = column_axial_kn_per_m  # kN/m = N/mm

        m = _new_model()
        _add_section(m, "col_sec", self.col_sec)
        _add_section(m, "raf_sec", self.raf_sec)

        # Nodes
        m.add_node("BL",          0,          0, 0)
        m.add_node("EL",          0,  eaves_h_mm, 0)
        m.add_node("AP", half_span_mm, apex_h_mm, 0)
        m.add_node("ER",      span_mm, eaves_h_mm, 0)
        m.add_node("BR",      span_mm,          0, 0)

        # Supports
        _pin_support(m, "BL")
        _pin_support(m, "BR")
        _fix_out_of_plane(m, "EL")
        _fix_out_of_plane(m, "AP")
        _fix_out_of_plane(m, "ER")

        # Members
        m.add_member("COL_L", "BL", "EL", "steel", "col_sec")
        m.add_member("RAF_L", "EL", "AP", "steel", "raf_sec")
        m.add_member("RAF_R", "AP", "ER", "steel", "raf_sec")
        m.add_member("COL_R", "ER", "BR", "steel", "col_sec")

        # Loads
        if rafter_udl_kn_per_m != 0.0:
            m.add_member_dist_load("RAF_L", "Fy", -w_raf_n_mm, -w_raf_n_mm, case="DL")
            m.add_member_dist_load("RAF_R", "Fy", -w_raf_n_mm, -w_raf_n_mm, case="DL")
        if column_axial_kn_per_m != 0.0:
            m.add_member_dist_load("COL_L", "Fy", -w_col_n_mm, -w_col_n_mm, case="DL")
            m.add_member_dist_load("COL_R", "Fy", -w_col_n_mm, -w_col_n_mm, case="DL")

        m.add_load_combo(_COMBO, {"DL": 1.0})
        m.analyze_linear(log=False, check_stability=False)

        # Extract forces at salient points
        def _forces_at_node(location: str, node_name: str, member_name: str, x_mm: float) -> MemberForces:
            N_kn  = m.members[member_name].axial(x_mm, _COMBO) / 1_000.0
            V_kn  = m.members[member_name].shear("Fy", x_mm, _COMBO) / 1_000.0
            Mz_knm = m.members[member_name].moment("Mz", x_mm, _COMBO) / 1_000_000.0
            return MemberForces(location=location, axial_kn=N_kn, shear_kn=V_kn, moment_knm=Mz_knm)

        col_l_len = eaves_h_mm
        raf_l_len = rafter_len_mm

        # col_base_L: at x=0 on COL_L, but pinned so moment=0; use reactions for correctness
        # We read directly from the member at x=0 (i-end)
        col_base_L = MemberForces(
            location="col_base_L",
            axial_kn   = m.members["COL_L"].axial(0.0, _COMBO) / 1_000.0,
            shear_kn   = m.members["COL_L"].shear("Fy",  0.0, _COMBO) / 1_000.0,
            moment_knm = m.members["COL_L"].moment("Mz", 0.0, _COMBO) / 1_000_000.0,
        )
        eaves_L = MemberForces(
            location="eaves_L",
            axial_kn   = m.members["COL_L"].axial(col_l_len, _COMBO) / 1_000.0,
            shear_kn   = m.members["COL_L"].shear("Fy",  col_l_len, _COMBO) / 1_000.0,
            moment_knm = m.members["COL_L"].moment("Mz", col_l_len, _COMBO) / 1_000_000.0,
        )
        apex = MemberForces(
            location="apex",
            axial_kn   = m.members["RAF_L"].axial(raf_l_len, _COMBO) / 1_000.0,
            shear_kn   = m.members["RAF_L"].shear("Fy",  raf_l_len, _COMBO) / 1_000.0,
            moment_knm = m.members["RAF_L"].moment("Mz", raf_l_len, _COMBO) / 1_000_000.0,
        )
        eaves_R = MemberForces(
            location="eaves_R",
            axial_kn   = m.members["COL_R"].axial(0.0, _COMBO) / 1_000.0,
            shear_kn   = m.members["COL_R"].shear("Fy",  0.0, _COMBO) / 1_000.0,
            moment_knm = m.members["COL_R"].moment("Mz", 0.0, _COMBO) / 1_000_000.0,
        )
        col_base_R = MemberForces(
            location="col_base_R",
            axial_kn   = m.members["COL_R"].axial(col_l_len, _COMBO) / 1_000.0,
            shear_kn   = m.members["COL_R"].shear("Fy",  col_l_len, _COMBO) / 1_000.0,
            moment_knm = m.members["COL_R"].moment("Mz", col_l_len, _COMBO) / 1_000_000.0,
        )

        return AnalysisResult(
            combination=combination_name,
            forces=[col_base_L, eaves_L, apex, eaves_R, col_base_R],
        )

    def run_wind_combination(
        self,
        combination_name: str,
        *,
        rafter_dead_udl_kn_per_m: float,
        column_dead_udl_kn_per_m: float,
        windward_column_udl_kn_per_m: float,
        leeward_column_udl_kn_per_m: float,
        windward_rafter_udl_kn_per_m: float,
        leeward_rafter_udl_kn_per_m: float,
    ) -> AnalysisResult:
        """Analyse a wind load combination (factored dead + factored transverse wind).

        PROVISIONAL — the wind-on-frame application (sign conventions, asymmetric
        windward/leeward loading) must be validated against SANS worked examples by a
        registered engineer before use. Wind from the LEFT (windward = left column / RAF_L).

        All UDLs are already FACTORED by the caller (kN/m = N/mm numerically). Conventions:
          * dead rafter/column: vertical, downward (local Fy, as gravity ``run``);
          * column wind: horizontal, +ve = inward pressure (global FX: +X left, −X right);
          * rafter wind: normal to roof, +ve = pressure onto roof / −ve = uplift (local Fy).

        Returns forces at col_base_L, eaves_L, apex, eaves_R, col_base_R — read directly
        from the analysis (no symmetry assumptions; both columns differ under wind).
        """
        m, eaves_h_mm, rafter_len_mm = self._build_wind_model(
            rafter_dead_udl_kn_per_m=rafter_dead_udl_kn_per_m,
            column_dead_udl_kn_per_m=column_dead_udl_kn_per_m,
            windward_column_udl_kn_per_m=windward_column_udl_kn_per_m,
            leeward_column_udl_kn_per_m=leeward_column_udl_kn_per_m,
            windward_rafter_udl_kn_per_m=windward_rafter_udl_kn_per_m,
            leeward_rafter_udl_kn_per_m=leeward_rafter_udl_kn_per_m,
        )

        def _f(location: str, member: str, x_mm: float) -> MemberForces:
            return MemberForces(
                location=location,
                axial_kn=m.members[member].axial(x_mm, _COMBO) / 1_000.0,
                shear_kn=m.members[member].shear("Fy", x_mm, _COMBO) / 1_000.0,
                moment_knm=m.members[member].moment("Mz", x_mm, _COMBO) / 1_000_000.0,
            )

        return AnalysisResult(
            combination=combination_name,
            forces=[
                _f("col_base_L", "COL_L", 0.0),
                _f("eaves_L", "COL_L", eaves_h_mm),
                _f("apex", "RAF_L", rafter_len_mm),
                _f("eaves_R", "COL_R", 0.0),
                _f("col_base_R", "COL_R", eaves_h_mm),
            ],
        )

    def wind_combination_displacements(
        self,
        *,
        rafter_dead_udl_kn_per_m: float,
        column_dead_udl_kn_per_m: float,
        windward_column_udl_kn_per_m: float,
        leeward_column_udl_kn_per_m: float,
        windward_rafter_udl_kn_per_m: float,
        leeward_rafter_udl_kn_per_m: float,
    ) -> dict[str, dict[str, float]]:
        """Node displacements (DX/DY, mm) under a factored transverse-wind combination.

        Same model + loading as :meth:`run_wind_combination`; used for the SLS-2 eaves-sway
        (lateral drift) check. PROVISIONAL — inherits the wind-on-frame sign conventions of
        :meth:`run_wind_combination`, which require registered-engineer validation.

        Returns ``{node: {"DX": mm, "DY": mm}}`` for nodes BL, EL, AP, ER, BR (DX = lateral,
        DY positive = up).
        """
        m, _, _ = self._build_wind_model(
            rafter_dead_udl_kn_per_m=rafter_dead_udl_kn_per_m,
            column_dead_udl_kn_per_m=column_dead_udl_kn_per_m,
            windward_column_udl_kn_per_m=windward_column_udl_kn_per_m,
            leeward_column_udl_kn_per_m=leeward_column_udl_kn_per_m,
            windward_rafter_udl_kn_per_m=windward_rafter_udl_kn_per_m,
            leeward_rafter_udl_kn_per_m=leeward_rafter_udl_kn_per_m,
        )
        result: dict[str, dict[str, float]] = {}
        for node_name in ("BL", "EL", "AP", "ER", "BR"):
            node = m.nodes[node_name]
            result[node_name] = {"DX": node.DX[_COMBO], "DY": node.DY[_COMBO]}
        return result

    def _build_wind_model(
        self,
        *,
        rafter_dead_udl_kn_per_m: float,
        column_dead_udl_kn_per_m: float,
        windward_column_udl_kn_per_m: float,
        leeward_column_udl_kn_per_m: float,
        windward_rafter_udl_kn_per_m: float,
        leeward_rafter_udl_kn_per_m: float,
    ) -> tuple[FEModel3D, float, float]:
        """Build, load and solve the transverse-wind portal model.

        Returns ``(analysed_model, eaves_h_mm, rafter_len_mm)``. All UDLs are already
        FACTORED by the caller (kN/m = N/mm numerically). Conventions are documented on
        :meth:`run_wind_combination`. PROVISIONAL — see that method.
        """
        geom = self.spec.geometry
        span_mm = geom.span_m * 1_000.0
        eaves_h_mm = geom.eaves_height_m * 1_000.0
        apex_h_mm = geom.apex_height_m * 1_000.0
        half_span_mm = span_mm / 2.0
        rafter_len_mm = math.hypot(half_span_mm, apex_h_mm - eaves_h_mm)

        m = _new_model()
        _add_section(m, "col_sec", self.col_sec)
        _add_section(m, "raf_sec", self.raf_sec)
        m.add_node("BL", 0, 0, 0)
        m.add_node("EL", 0, eaves_h_mm, 0)
        m.add_node("AP", half_span_mm, apex_h_mm, 0)
        m.add_node("ER", span_mm, eaves_h_mm, 0)
        m.add_node("BR", span_mm, 0, 0)
        _pin_support(m, "BL")
        _pin_support(m, "BR")
        _fix_out_of_plane(m, "EL")
        _fix_out_of_plane(m, "AP")
        _fix_out_of_plane(m, "ER")
        m.add_member("COL_L", "BL", "EL", "steel", "col_sec")
        m.add_member("RAF_L", "EL", "AP", "steel", "raf_sec")
        m.add_member("RAF_R", "AP", "ER", "steel", "raf_sec")
        m.add_member("COL_R", "ER", "BR", "steel", "col_sec")

        # Dead (vertical, local Fy downward)
        rd = rafter_dead_udl_kn_per_m
        cd = column_dead_udl_kn_per_m
        if rd != 0.0:
            m.add_member_dist_load("RAF_L", "Fy", -rd, -rd, case="DL")
            m.add_member_dist_load("RAF_R", "Fy", -rd, -rd, case="DL")
        if cd != 0.0:
            m.add_member_dist_load("COL_L", "Fy", -cd, -cd, case="DL")
            m.add_member_dist_load("COL_R", "Fy", -cd, -cd, case="DL")

        # Wind on columns (global horizontal FX; +ve udl = inward pressure)
        ww_c = windward_column_udl_kn_per_m
        lw_c = leeward_column_udl_kn_per_m
        if ww_c != 0.0:
            m.add_member_dist_load("COL_L", "FX", ww_c, ww_c, case="DL")  # left: inward = +X
        if lw_c != 0.0:
            m.add_member_dist_load("COL_R", "FX", -lw_c, -lw_c, case="DL")  # right: inward = −X

        # Wind on rafters (local Fy normal; +ve = pressure onto roof, −ve = uplift)
        ww_r = windward_rafter_udl_kn_per_m
        lw_r = leeward_rafter_udl_kn_per_m
        if ww_r != 0.0:
            m.add_member_dist_load("RAF_L", "Fy", -ww_r, -ww_r, case="DL")
        if lw_r != 0.0:
            m.add_member_dist_load("RAF_R", "Fy", -lw_r, -lw_r, case="DL")

        m.add_load_combo(_COMBO, {"DL": 1.0})
        m.analyze_linear(log=False, check_stability=False)
        return m, eaves_h_mm, rafter_len_mm

    def node_displacements(
        self,
        combination_name: str,
        rafter_udl_kn_per_m: float,
        column_axial_kn_per_m: float = 0.0,
    ) -> dict[str, dict[str, float]]:
        """Analyse and return node displacements (mm) at portal key points.

        Same loading as :meth:`run`; runs a fresh analysis to return DX/DY at each node.

        Returns
        -------
        dict mapping node name → {"DX": float, "DY": float} (mm).
            Nodes: "BL", "EL", "AP", "ER", "BR".
        """
        geom = self.spec.geometry
        span_mm      = geom.span_m          * 1_000.0
        eaves_h_mm   = geom.eaves_height_m  * 1_000.0
        apex_h_mm    = geom.apex_height_m   * 1_000.0
        half_span_mm = span_mm / 2.0

        w_raf_n_mm = rafter_udl_kn_per_m
        w_col_n_mm = column_axial_kn_per_m

        m = _new_model()
        _add_section(m, "col_sec", self.col_sec)
        _add_section(m, "raf_sec", self.raf_sec)

        m.add_node("BL",          0,          0, 0)
        m.add_node("EL",          0,  eaves_h_mm, 0)
        m.add_node("AP", half_span_mm, apex_h_mm, 0)
        m.add_node("ER",      span_mm, eaves_h_mm, 0)
        m.add_node("BR",      span_mm,          0, 0)

        _pin_support(m, "BL")
        _pin_support(m, "BR")
        _fix_out_of_plane(m, "EL")
        _fix_out_of_plane(m, "AP")
        _fix_out_of_plane(m, "ER")

        m.add_member("COL_L", "BL", "EL", "steel", "col_sec")
        m.add_member("RAF_L", "EL", "AP", "steel", "raf_sec")
        m.add_member("RAF_R", "AP", "ER", "steel", "raf_sec")
        m.add_member("COL_R", "ER", "BR", "steel", "col_sec")

        if rafter_udl_kn_per_m != 0.0:
            m.add_member_dist_load("RAF_L", "Fy", -w_raf_n_mm, -w_raf_n_mm, case="DL")
            m.add_member_dist_load("RAF_R", "Fy", -w_raf_n_mm, -w_raf_n_mm, case="DL")
        if column_axial_kn_per_m != 0.0:
            m.add_member_dist_load("COL_L", "Fy", -w_col_n_mm, -w_col_n_mm, case="DL")
            m.add_member_dist_load("COL_R", "Fy", -w_col_n_mm, -w_col_n_mm, case="DL")

        m.add_load_combo(_COMBO, {"DL": 1.0})
        m.analyze_linear(log=False, check_stability=False)

        result: dict[str, dict[str, float]] = {}
        for node_name in ("BL", "EL", "AP", "ER", "BR"):
            node = m.nodes[node_name]
            result[node_name] = {
                "DX": node.DX[_COMBO],   # lateral displacement (mm)
                "DY": node.DY[_COMBO],   # vertical displacement (mm, positive = up)
            }
        return result
