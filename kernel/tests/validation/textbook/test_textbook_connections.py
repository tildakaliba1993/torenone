"""Connection-mechanics validation vs the SECOND authority — Mahachi, *Design of Structural
Steelwork to SANS 10162* (CSIR, 2004), Chapter 7, worked Examples **E7.5–E7.9**.

Proves the methods in ``torenone_kernel.connections.textbook`` reproduce the book's published
answers: the elastic bolt-group method (E7.6 web splice, E7.7 eccentric bracket, E7.9 side plates)
and the Eurocode-3 T-stub prying method (E7.5) — the prying check our portal end-plate
(`connections/moment_endplate.py`) currently omits.

PROVISIONAL: validated but not yet wired into the live design path — awaits registered-engineer
sign-off (see docs/REDBOOK-VALIDATION.md). Only numeric facts are encoded; each cites its example.
Must-pass.
"""

from __future__ import annotations

import pytest
from torenone_kernel.connections.textbook import (
    bolt_group_resultant,
    tstub_prying_bolt_tension,
)

_SRC = "Mahachi, Design of Structural Steelwork to SANS 10162 (CSIR, 2004)"
_TOL = 0.02


# --- Elastic bolt-group method (eq. 7.27) ---------------------------------------------------

def test_e7_7_eccentric_bracket() -> None:
    # E7.7: 10 bolts (2 cols x=±45, 5 rows y=0,±70,±140); 90 kN down at e=275 mm → 34.6 kN/bolt.
    bolts = [(x, y) for x in (-45.0, 45.0) for y in (-140.0, -70.0, 0.0, 70.0, 140.0)]
    res = bolt_group_resultant(bolts, shear_x_kn=0.0, shear_y_kn=-90.0, in_plane_moment_knm=90.0 * 0.275)
    assert res.moment_force_kn == pytest.approx(30.8, rel=_TOL), f"{_SRC} E7.7: V_M vs 30.8 kN"
    assert res.resultant_kn == pytest.approx(34.6, rel=_TOL), f"{_SRC} E7.7: V_ub vs 34.6 kN"


def test_e7_9_side_plate_shear_and_moment() -> None:
    # E7.9: 8 bolts (x=±80, y=±80,±240); Vu=125, Hu=12.5 per side, M=66 kN·m → 62.5 kN/bolt.
    bolts = [(x, y) for x in (-80.0, 80.0) for y in (-240.0, -80.0, 80.0, 240.0)]
    res = bolt_group_resultant(bolts, shear_x_kn=12.5, shear_y_kn=-125.0, in_plane_moment_knm=66.0)
    assert res.resultant_kn == pytest.approx(62.5, rel=_TOL), f"{_SRC} E7.9: V_R vs 62.5 kN"


def test_e7_6_web_splice() -> None:
    # E7.6 (simplified web splice): 4 bolts in a line (y=±50,±150); Vu=300 kN at e=45 mm
    # → vertical 75, moment 40.5, resultant 85.2 kN/bolt.
    bolts = [(0.0, y) for y in (-150.0, -50.0, 50.0, 150.0)]
    res = bolt_group_resultant(bolts, shear_x_kn=0.0, shear_y_kn=-300.0, in_plane_moment_knm=300.0 * 0.045)
    assert res.direct_fy_kn == pytest.approx(-75.0, rel=_TOL), f"{_SRC} E7.6: Vv vs 75 kN"
    assert res.moment_force_kn == pytest.approx(40.5, rel=_TOL), f"{_SRC} E7.6: V_M vs 40.5 kN"
    assert res.resultant_kn == pytest.approx(85.2, rel=_TOL), f"{_SRC} E7.6: V_ub vs 85.2 kN"


# --- Eurocode-3 T-stub prying (§7.5.1 / E7.5) -----------------------------------------------

def test_e7_5_tstub_prying() -> None:
    # E7.5: T-stub from 457×191×90 (tf=17.7, tw=10.6, r=10.2), 4×M20-8.8 at 100 mm cross-centres,
    # Pu=240 kN. Prying raises the bolt force from 60 (no prying) to 68.6 kN (+14.3%).
    res = tstub_prying_bolt_tension(
        applied_force_kn=240.0,
        n_bolts=4,
        gauge_mm=100.0,
        flange_width_mm=192.0,
        flange_thickness_mm=17.7,
        web_thickness_mm=10.6,
        root_radius_mm=10.2,
        bolt_pitch_mm=70.0,
        end_distance_mm=50.0,
        fy_mpa=300.0,
    )
    assert res.m_mm == pytest.approx(36.5, rel=_TOL), f"{_SRC} E7.5: m vs 36.5 mm"
    assert res.n_mm == pytest.approx(45.6, rel=_TOL), f"{_SRC} E7.5: n vs 45.6 mm"
    assert res.sum_l_eff_mm == pytest.approx(170.0, rel=_TOL), f"{_SRC} E7.5: Σl_eff vs 170 mm"
    assert res.moment_resistance_nmm == pytest.approx(3.60e6, rel=_TOL), f"{_SRC} E7.5: Mr vs 3.60e6 N·mm"
    assert res.bolt_tension_kn == pytest.approx(68.6, rel=_TOL), f"{_SRC} E7.5: Tu vs 68.6 kN"
    assert res.prying_increase_pct == pytest.approx(14.3, rel=0.05), f"{_SRC} E7.5: prying +14.3%"
