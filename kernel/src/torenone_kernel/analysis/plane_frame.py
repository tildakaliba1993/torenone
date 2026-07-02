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
from typing import NamedTuple

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


def _forces_at(model: FEModel3D, location: str, member_name: str, x_mm: float) -> MemberForces:
    """Axial (kN), shear (kN, "Fy") and moment (kN·m, "Mz") at *x_mm* on a member.

    The shared last-mile convention (matches PortalAnalysis force extraction): N→kN, N·mm→kN·m.
    """
    return MemberForces(
        location=location,
        axial_kn=model.members[member_name].axial(x_mm, _COMBO) / 1_000.0,
        shear_kn=model.members[member_name].shear("Fy", x_mm, _COMBO) / 1_000.0,
        moment_knm=model.members[member_name].moment("Mz", x_mm, _COMBO) / 1_000_000.0,
    )


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


class MultiSpanStatics(NamedTuple):
    """Statics of a multi-span portal solve — enough to verify equilibrium + load share.

    Reactions are per base, left→right (index 0 = leftmost). Moments are magnitudes (N·mm).
    """

    V_N: tuple[float, ...]           # vertical reaction at each base (signed: up +)
    H_N: tuple[float, ...]           # horizontal reaction at each base (signed)
    M_eaves_ext_Nmm: float           # bending moment at an external eaves (top of end column)
    M_eaves_int_Nmm: float | None    # ...at an internal (valley) eaves; None for a single span
    M_ridge_Nmm: float               # bending moment at a ridge
    total_vertical_N: float          # total applied gravity (w × Σ rafter length)

    @property
    def sum_V_N(self) -> float:
        return sum(self.V_N)

    @property
    def sum_H_N(self) -> float:
        return sum(self.H_N)


def solve_multispan_udl(
    span_mm: float,
    eaves_mm: float,
    apex_mm: float,
    n_spans: int,
    w_n_per_mm: float,
    ext_col_section: SectionProperties,
    int_col_section: SectionProperties,
    raf_section: SectionProperties,
) -> MultiSpanStatics:
    """Solve a pinned-base **multi-span** (duopitch) portal frame under a vertical UDL.

    PROVISIONAL — new geometry (Path B), pending registered-engineer validation. ``n_spans`` equal
    duopitch spans side by side share internal (valley) columns; every base is pinned. Gravity is
    applied as a GLOBAL vertical load (``"FY"``, per unit rafter length) — the physically correct
    convention (as in :func:`solve_monopitch_udl`), so at zero pitch it coincides with the flat
    :func:`solve_portal_udl`.

    Geometry (equal spans of width ``span_mm``), for i in 0..n_spans:
        base   Bi at (i·span, 0)          eaves/valley  Ei at (i·span, eaves)
    and for each span s in 0..n_spans-1:
        ridge  Rs at ((s+0.5)·span, apex)

    Columns C0 and C{n_spans} are external; the rest are internal. Rafters run Es→Rs→E{s+1}.
    """
    if n_spans < 1:
        raise ValueError("n_spans must be >= 1")

    raf_half_len_mm = math.hypot(span_mm / 2.0, apex_mm - eaves_mm)

    m = _new_model()
    _add_section(m, "ext_col", ext_col_section)
    _add_section(m, "int_col", int_col_section)
    _add_section(m, "raf", raf_section)

    # Nodes: bases + eaves at each gridline, ridge at each span mid-point.
    for i in range(n_spans + 1):
        x = i * span_mm
        m.add_node(f"B{i}", x, 0, 0)
        m.add_node(f"E{i}", x, eaves_mm, 0)
        _pin_support(m, f"B{i}")
        _fix_out_of_plane(m, f"E{i}")
    for s in range(n_spans):
        m.add_node(f"R{s}", (s + 0.5) * span_mm, apex_mm, 0)
        _fix_out_of_plane(m, f"R{s}")

    # Columns (external at the two ends, internal between spans).
    for i in range(n_spans + 1):
        sec = "ext_col" if (i == 0 or i == n_spans) else "int_col"
        m.add_member(f"C{i}", f"B{i}", f"E{i}", "steel", sec)
    # Rafters: two per span (eaves→ridge, ridge→eaves).
    for s in range(n_spans):
        m.add_member(f"RL{s}", f"E{s}", f"R{s}", "steel", "raf")
        m.add_member(f"RR{s}", f"R{s}", f"E{s + 1}", "steel", "raf")
        m.add_member_dist_load(f"RL{s}", "FY", -w_n_per_mm, -w_n_per_mm, case="DL")
        m.add_member_dist_load(f"RR{s}", "FY", -w_n_per_mm, -w_n_per_mm, case="DL")

    _add_load_combo(m)
    m.analyze_linear(log=False, check_stability=False)

    v_reactions = tuple(float(m.nodes[f"B{i}"].RxnFY[_COMBO]) for i in range(n_spans + 1))
    h_reactions = tuple(float(m.nodes[f"B{i}"].RxnFX[_COMBO]) for i in range(n_spans + 1))

    # Moment at the top of the leftmost (external) column; and an internal column if present.
    m_eaves_ext = abs(m.members["C0"].moment("Mz", eaves_mm, _COMBO))
    m_eaves_int = (
        abs(m.members["C1"].moment("Mz", eaves_mm, _COMBO)) if n_spans >= 2 else None
    )
    m_ridge = abs(m.members["RL0"].moment("Mz", raf_half_len_mm, _COMBO))
    total_vertical = w_n_per_mm * raf_half_len_mm * 2.0 * n_spans

    return MultiSpanStatics(
        V_N=v_reactions,
        H_N=h_reactions,
        M_eaves_ext_Nmm=m_eaves_ext,
        M_eaves_int_Nmm=m_eaves_int,
        M_ridge_Nmm=m_ridge,
        total_vertical_N=total_vertical,
    )


class MonopitchDemand(NamedTuple):
    """Governing member demands for a mono-pitch frame under one gravity combination (kN / kN·m).

    Each member's axial/shear/moment is the worst (envelope max) over the member — conservative
    for sizing. ``rafter_sag_mm`` is the max rafter transverse deflection (for the SLS check).
    """

    rafter_cu_kn: float
    rafter_vu_kn: float
    rafter_mu_knm: float
    low_col_cu_kn: float
    low_col_vu_kn: float
    low_col_mu_knm: float
    high_col_cu_kn: float
    high_col_vu_kn: float
    high_col_mu_knm: float
    rafter_sag_mm: float


class MonopitchAnalysis:
    """Mono-pitch (single-slope) pinned-base portal frame — PROVISIONAL (T1-3, sign-off D12).

    The asymmetric analogue of :class:`PortalAnalysis`: a low column, a single sloping rafter,
    and a high column. ``demand()`` returns the governing member forces (and rafter sag) for
    member sizing. Gravity is applied as a GLOBAL-vertical load (see `solve_monopitch_udl`).
    """

    _N_SAMPLES = 21

    def __init__(
        self, spec: FrameSpec, column_section: SectionProperties, rafter_section: SectionProperties
    ) -> None:
        self.spec = spec
        self.col_sec = column_section
        self.raf_sec = rafter_section

    def _build(self, w_raf_n_mm: float) -> tuple[FEModel3D, float, float, float]:
        geom = self.spec.geometry
        span_mm = geom.span_m * 1_000.0
        low_mm = geom.eaves_height_m * 1_000.0
        high_mm = geom.high_eaves_height_m * 1_000.0
        raf_len_mm = math.hypot(span_mm, high_mm - low_mm)

        m = _new_model()
        _add_section(m, "col_sec", self.col_sec)
        _add_section(m, "raf_sec", self.raf_sec)
        m.add_node("BL", 0, 0, 0)
        m.add_node("EL", 0, low_mm, 0)
        m.add_node("EH", span_mm, high_mm, 0)
        m.add_node("BH", span_mm, 0, 0)
        _pin_support(m, "BL")
        _pin_support(m, "BH")
        _fix_out_of_plane(m, "EL")
        _fix_out_of_plane(m, "EH")
        m.add_member("COL_L", "BL", "EL", "steel", "col_sec")
        m.add_member("RAF", "EL", "EH", "steel", "raf_sec")
        m.add_member("COL_H", "EH", "BH", "steel", "col_sec")
        m.add_member_dist_load("RAF", "FY", -w_raf_n_mm, -w_raf_n_mm, case="DL")
        _add_load_combo(m)
        m.analyze_linear(log=False, check_stability=False)
        return m, low_mm, high_mm, raf_len_mm

    def demand(self, rafter_udl_kn_per_m: float) -> MonopitchDemand:
        """Return the governing member demands for *rafter_udl_kn_per_m* (kN/m, downward +)."""
        m, low_mm, high_mm, raf_len_mm = self._build(rafter_udl_kn_per_m)

        def _envelope(member: str, length_mm: float) -> tuple[float, float, float, float]:
            cu = vu = mu = sag = 0.0
            for i in range(self._N_SAMPLES):
                x = length_mm * i / (self._N_SAMPLES - 1)
                cu = max(cu, abs(m.members[member].axial(x, _COMBO)))
                vu = max(vu, abs(m.members[member].shear("Fy", x, _COMBO)))
                mu = max(mu, abs(m.members[member].moment("Mz", x, _COMBO)))
                sag = max(sag, abs(m.members[member].deflection("dy", x, _COMBO)))
            return cu / 1e3, vu / 1e3, mu / 1e6, sag  # N→kN, N·mm→kN·m, mm

        raf_cu, raf_vu, raf_mu, raf_sag = _envelope("RAF", raf_len_mm)
        low_cu, low_vu, low_mu, _ = _envelope("COL_L", low_mm)
        high_cu, high_vu, high_mu, _ = _envelope("COL_H", high_mm)
        return MonopitchDemand(
            rafter_cu_kn=raf_cu, rafter_vu_kn=raf_vu, rafter_mu_knm=raf_mu,
            low_col_cu_kn=low_cu, low_col_vu_kn=low_vu, low_col_mu_knm=low_mu,
            high_col_cu_kn=high_cu, high_col_vu_kn=high_vu, high_col_mu_knm=high_mu,
            rafter_sag_mm=raf_sag,
        )

    def last_mile_forces(self, rafter_udl_kn_per_m: float) -> dict[str, MemberForces]:
        """Joint + base forces for the last mile (both eaves knees + both bases).

        Keys: ``eaves_low``/``eaves_high`` (the two knee connections) and ``base_low``/``base_high``
        (the two column bases). Forces are read off the same validated model as :meth:`demand`.
        """
        m, low_mm, high_mm, _ = self._build(rafter_udl_kn_per_m)
        return {
            "base_low": _forces_at(m, "base_low", "COL_L", 0.0),
            "eaves_low": _forces_at(m, "eaves_low", "COL_L", low_mm),
            "eaves_high": _forces_at(m, "eaves_high", "COL_H", 0.0),  # COL_H i-end = high eaves
            "base_high": _forces_at(m, "base_high", "COL_H", high_mm),
        }

    def _build_wind_model(
        self,
        *,
        rafter_dead_udl_kn_per_m: float,
        column_dead_udl_kn_per_m: float,
        low_column_wind_udl_kn_per_m: float,
        high_column_wind_udl_kn_per_m: float,
        rafter_wind_udl_kn_per_m: float,
    ) -> tuple[FEModel3D, float, float, float]:
        """Build, load and solve a mono-pitch wind combination (factored dead + transverse wind).

        PROVISIONAL (D12 wind) — the wind-on-frame application (sign conventions, asymmetric
        low/high loading) must be validated against SANS worked examples by a registered engineer.
        All UDLs are already FACTORED by the caller (kN/m = N/mm numerically). Conventions mirror
        :meth:`PortalAnalysis._build_wind_model`:
          * dead: GLOBAL vertical, downward (``FY``), on the rafter and both columns;
          * column wind: GLOBAL horizontal (``FX``) — the LOW column (x=0) takes ``+X`` × its UDL,
            the HIGH column (x=span) takes ``−X`` × its UDL, so each UDL's sign (pressure +, suction
            −) resolves to the correct inward/outward direction for BOTH wind directions;
          * rafter wind: NORMAL to the roof (local ``Fy``), applied as ``−UDL`` (matching the
            duopitch convention: +ve UDL = pressure onto the roof, −ve = uplift).
        """
        geom = self.spec.geometry
        span_mm = geom.span_m * 1_000.0
        low_mm = geom.eaves_height_m * 1_000.0
        high_mm = geom.high_eaves_height_m * 1_000.0
        raf_len_mm = math.hypot(span_mm, high_mm - low_mm)

        m = _new_model()
        _add_section(m, "col_sec", self.col_sec)
        _add_section(m, "raf_sec", self.raf_sec)
        m.add_node("BL", 0, 0, 0)
        m.add_node("EL", 0, low_mm, 0)
        m.add_node("EH", span_mm, high_mm, 0)
        m.add_node("BH", span_mm, 0, 0)
        _pin_support(m, "BL")
        _pin_support(m, "BH")
        _fix_out_of_plane(m, "EL")
        _fix_out_of_plane(m, "EH")
        m.add_member("COL_L", "BL", "EL", "steel", "col_sec")
        m.add_member("RAF", "EL", "EH", "steel", "raf_sec")
        m.add_member("COL_H", "EH", "BH", "steel", "col_sec")

        rd = rafter_dead_udl_kn_per_m
        cd = column_dead_udl_kn_per_m
        if rd != 0.0:
            m.add_member_dist_load("RAF", "FY", -rd, -rd, case="DL")
        if cd != 0.0:
            m.add_member_dist_load("COL_L", "FY", -cd, -cd, case="DL")
            m.add_member_dist_load("COL_H", "FY", -cd, -cd, case="DL")

        low_c = low_column_wind_udl_kn_per_m
        high_c = high_column_wind_udl_kn_per_m
        if low_c != 0.0:
            m.add_member_dist_load("COL_L", "FX", low_c, low_c, case="DL")  # low col: +X
        if high_c != 0.0:
            m.add_member_dist_load("COL_H", "FX", -high_c, -high_c, case="DL")  # high col: −X

        rw = rafter_wind_udl_kn_per_m
        if rw != 0.0:
            m.add_member_dist_load("RAF", "Fy", -rw, -rw, case="DL")

        m.add_load_combo(_COMBO, {"DL": 1.0})
        m.analyze_linear(log=False, check_stability=False)
        return m, low_mm, high_mm, raf_len_mm

    def run_wind_combination(
        self,
        *,
        rafter_dead_udl_kn_per_m: float,
        column_dead_udl_kn_per_m: float,
        low_column_wind_udl_kn_per_m: float,
        high_column_wind_udl_kn_per_m: float,
        rafter_wind_udl_kn_per_m: float,
    ) -> MonopitchDemand:
        """Governing member demands under a factored mono-pitch wind combination.

        Same envelope basis as :meth:`demand` (worst |N|,|V|,|M| over each member). PROVISIONAL —
        see :meth:`_build_wind_model`. ``rafter_sag_mm`` is 0.0 here (sag is an SLS-gravity check).
        """
        m, low_mm, high_mm, raf_len_mm = self._build_wind_model(
            rafter_dead_udl_kn_per_m=rafter_dead_udl_kn_per_m,
            column_dead_udl_kn_per_m=column_dead_udl_kn_per_m,
            low_column_wind_udl_kn_per_m=low_column_wind_udl_kn_per_m,
            high_column_wind_udl_kn_per_m=high_column_wind_udl_kn_per_m,
            rafter_wind_udl_kn_per_m=rafter_wind_udl_kn_per_m,
        )

        def _envelope(member: str, length_mm: float) -> tuple[float, float, float]:
            cu = vu = mu = 0.0
            for i in range(self._N_SAMPLES):
                x = length_mm * i / (self._N_SAMPLES - 1)
                cu = max(cu, abs(m.members[member].axial(x, _COMBO)))
                vu = max(vu, abs(m.members[member].shear("Fy", x, _COMBO)))
                mu = max(mu, abs(m.members[member].moment("Mz", x, _COMBO)))
            return cu / 1e3, vu / 1e3, mu / 1e6  # N→kN, N·mm→kN·m

        raf_cu, raf_vu, raf_mu = _envelope("RAF", raf_len_mm)
        low_cu, low_vu, low_mu = _envelope("COL_L", low_mm)
        high_cu, high_vu, high_mu = _envelope("COL_H", high_mm)
        return MonopitchDemand(
            rafter_cu_kn=raf_cu, rafter_vu_kn=raf_vu, rafter_mu_knm=raf_mu,
            low_col_cu_kn=low_cu, low_col_vu_kn=low_vu, low_col_mu_knm=low_mu,
            high_col_cu_kn=high_cu, high_col_vu_kn=high_vu, high_col_mu_knm=high_mu,
            rafter_sag_mm=0.0,
        )

    def wind_combination_displacements(
        self,
        *,
        rafter_dead_udl_kn_per_m: float,
        column_dead_udl_kn_per_m: float,
        low_column_wind_udl_kn_per_m: float,
        high_column_wind_udl_kn_per_m: float,
        rafter_wind_udl_kn_per_m: float,
    ) -> dict[str, dict[str, float]]:
        """Node displacements (DX/DY, mm) under a factored mono-pitch wind combination.

        Same model as :meth:`run_wind_combination`; used for the SLS-2 eaves-sway check.
        Returns ``{node: {"DX", "DY"}}`` for BL, EL (low eaves), EH (high eaves), BH.
        """
        m, _, _, _ = self._build_wind_model(
            rafter_dead_udl_kn_per_m=rafter_dead_udl_kn_per_m,
            column_dead_udl_kn_per_m=column_dead_udl_kn_per_m,
            low_column_wind_udl_kn_per_m=low_column_wind_udl_kn_per_m,
            high_column_wind_udl_kn_per_m=high_column_wind_udl_kn_per_m,
            rafter_wind_udl_kn_per_m=rafter_wind_udl_kn_per_m,
        )
        out: dict[str, dict[str, float]] = {}
        for node_name in ("BL", "EL", "EH", "BH"):
            node = m.nodes[node_name]
            out[node_name] = {"DX": node.DX[_COMBO], "DY": node.DY[_COMBO]}
        return out


class MultiSpanDemand(NamedTuple):
    """Governing member demands for a multi-span frame (kN / kN·m), plus max rafter sag (mm)."""

    rafter_cu_kn: float
    rafter_vu_kn: float
    rafter_mu_knm: float
    rafter_sag_mm: float
    ext_col_cu_kn: float
    ext_col_vu_kn: float
    ext_col_mu_knm: float
    int_col_cu_kn: float
    int_col_vu_kn: float
    int_col_mu_knm: float


class MultiSpanAnalysis:
    """Multi-span (internal-column) pinned-base portal frame — PROVISIONAL (Path B, sign-off D13).

    ``n_spans`` equal duopitch spans sharing valley columns. ``demand()`` returns the governing
    forces for the external columns, the internal (valley) columns, and the rafters (worst of all),
    plus the max rafter sag — enough to size every member. Gravity is a GLOBAL-vertical load, as in
    :func:`solve_multispan_udl`.
    """

    _N_SAMPLES = 21

    def __init__(
        self,
        spec: FrameSpec,
        ext_col_section: SectionProperties,
        int_col_section: SectionProperties,
        rafter_section: SectionProperties,
    ) -> None:
        self.spec = spec
        self.ext_col_sec = ext_col_section
        self.int_col_sec = int_col_section
        self.raf_sec = rafter_section

    def _build(self, w_raf_n_mm: float) -> tuple[FEModel3D, float, float, int]:
        geom = self.spec.geometry
        span_mm = geom.span_m * 1_000.0
        eaves_mm = geom.eaves_height_m * 1_000.0
        apex_mm = geom.apex_height_m * 1_000.0
        n_spans = geom.number_of_spans
        raf_half_len_mm = math.hypot(span_mm / 2.0, apex_mm - eaves_mm)

        m = _new_model()
        _add_section(m, "ext_col", self.ext_col_sec)
        _add_section(m, "int_col", self.int_col_sec)
        _add_section(m, "raf", self.raf_sec)
        for i in range(n_spans + 1):
            x = i * span_mm
            m.add_node(f"B{i}", x, 0, 0)
            m.add_node(f"E{i}", x, eaves_mm, 0)
            _pin_support(m, f"B{i}")
            _fix_out_of_plane(m, f"E{i}")
        for s in range(n_spans):
            m.add_node(f"R{s}", (s + 0.5) * span_mm, apex_mm, 0)
            _fix_out_of_plane(m, f"R{s}")
        for i in range(n_spans + 1):
            sec = "ext_col" if (i == 0 or i == n_spans) else "int_col"
            m.add_member(f"C{i}", f"B{i}", f"E{i}", "steel", sec)
        for s in range(n_spans):
            m.add_member(f"RL{s}", f"E{s}", f"R{s}", "steel", "raf")
            m.add_member(f"RR{s}", f"R{s}", f"E{s + 1}", "steel", "raf")
            m.add_member_dist_load(f"RL{s}", "FY", -w_raf_n_mm, -w_raf_n_mm, case="DL")
            m.add_member_dist_load(f"RR{s}", "FY", -w_raf_n_mm, -w_raf_n_mm, case="DL")
        _add_load_combo(m)
        m.analyze_linear(log=False, check_stability=False)
        return m, eaves_mm, raf_half_len_mm, n_spans

    def demand(self, rafter_udl_kn_per_m: float) -> MultiSpanDemand:
        """Return the governing member demands for *rafter_udl_kn_per_m* (kN/m, downward +)."""
        m, eaves_mm, raf_half_len_mm, n_spans = self._build(rafter_udl_kn_per_m)

        def _envelope(member: str, length_mm: float) -> tuple[float, float, float, float]:
            cu = vu = mu = sag = 0.0
            for i in range(self._N_SAMPLES):
                x = length_mm * i / (self._N_SAMPLES - 1)
                cu = max(cu, abs(m.members[member].axial(x, _COMBO)))
                vu = max(vu, abs(m.members[member].shear("Fy", x, _COMBO)))
                mu = max(mu, abs(m.members[member].moment("Mz", x, _COMBO)))
                sag = max(sag, abs(m.members[member].deflection("dy", x, _COMBO)))
            return cu / 1e3, vu / 1e3, mu / 1e6, sag

        def _worst(members: list[str], length_mm: float) -> tuple[float, float, float, float]:
            cu = vu = mu = sag = 0.0
            for name in members:
                c, v, mo, s = _envelope(name, length_mm)
                cu, vu, mu, sag = max(cu, c), max(vu, v), max(mu, mo), max(sag, s)
            return cu, vu, mu, sag

        rafters = [f"RL{s}" for s in range(n_spans)] + [f"RR{s}" for s in range(n_spans)]
        raf_cu, raf_vu, raf_mu, raf_sag = _worst(rafters, raf_half_len_mm)

        ext_cols = [f"C{i}" for i in (0, n_spans)]
        ext_cu, ext_vu, ext_mu, _ = _worst(ext_cols, eaves_mm)

        int_cols = [f"C{i}" for i in range(1, n_spans)]
        int_cu, int_vu, int_mu = 0.0, 0.0, 0.0
        if int_cols:
            int_cu, int_vu, int_mu, _ = _worst(int_cols, eaves_mm)

        return MultiSpanDemand(
            rafter_cu_kn=raf_cu, rafter_vu_kn=raf_vu, rafter_mu_knm=raf_mu, rafter_sag_mm=raf_sag,
            ext_col_cu_kn=ext_cu, ext_col_vu_kn=ext_vu, ext_col_mu_knm=ext_mu,
            int_col_cu_kn=int_cu, int_col_vu_kn=int_vu, int_col_mu_knm=int_mu,
        )

    def last_mile_forces(self, rafter_udl_kn_per_m: float) -> dict[str, MemberForces]:
        """Joint + base forces for the last mile: an external and (if present) an internal line.

        Keys: ``eaves_ext``/``base_ext`` (an external column line) and, for >1 span,
        ``eaves_int``/``base_int`` (a valley column line). Columns run base(x=0)→eaves(x=eaves).
        """
        m, eaves_mm, _, n_spans = self._build(rafter_udl_kn_per_m)
        out = {
            "base_ext": _forces_at(m, "base_ext", "C0", 0.0),
            "eaves_ext": _forces_at(m, "eaves_ext", "C0", eaves_mm),
        }
        if n_spans >= 2:
            out["base_int"] = _forces_at(m, "base_int", "C1", 0.0)
            out["eaves_int"] = _forces_at(m, "eaves_int", "C1", eaves_mm)
        return out


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
