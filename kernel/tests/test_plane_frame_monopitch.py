"""Validation of the mono-pitch (single-slope) frame statics — T1-3 (PROVISIONAL).

This is the new geometry's foundation, so it is validated hard *before* anything sizes members
on it. We check the conditions a correct pinned-base frame solution MUST satisfy:

  1. Global equilibrium — vertical reactions carry the total applied vertical load; horizontal
     reactions sum to zero (no applied horizontal load). These are exact.
  2. Pinned bases — the base moments are (essentially) zero.
  3. Asymmetry — a mono-pitch frame is asymmetric, so the two eaves moments differ.
  4. Convergence — as the slope vanishes, the mono-pitch solution collapses onto the existing
     (validated) flat symmetric portal solver `solve_portal_udl`.

PROVISIONAL: the mono-pitch method awaits registered-engineer validation (sign-off pack D12).
Run: PYTHONPATH="kernel/src:tools" pytest kernel/tests/test_plane_frame_monopitch.py -q
"""

from __future__ import annotations

import math

import pytest
from torenone_kernel.analysis.plane_frame import solve_monopitch_udl, solve_portal_udl
from torenone_kernel.sections import SectionLibrary

_LIB = SectionLibrary.load_default()
_SEC = _LIB.get("356x171x51")

_SPAN = 20_000.0      # mm
_EAVES_LOW = 6_000.0  # mm
_W = 5.0              # N/mm (= 5 kN/m) downward on the rafter


def _eaves_high(pitch_deg: float) -> float:
    return _EAVES_LOW + _SPAN * math.tan(math.radians(pitch_deg))


def test_vertical_equilibrium() -> None:
    """Upward base reactions sum to the total applied vertical load."""
    r = solve_monopitch_udl(_SPAN, _EAVES_LOW, _eaves_high(10.0), _W, _SEC, _SEC)
    assert r["V_low_N"] + r["V_high_N"] == pytest.approx(r["total_vertical_N"], rel=1e-4)


def test_horizontal_equilibrium() -> None:
    """With no applied horizontal load, the two base horizontal reactions cancel."""
    r = solve_monopitch_udl(_SPAN, _EAVES_LOW, _eaves_high(10.0), _W, _SEC, _SEC)
    total_v = r["total_vertical_N"]
    assert r["H_low_N"] + r["H_high_N"] == pytest.approx(0.0, abs=1e-6 * total_v)


def test_pinned_bases_have_zero_moment() -> None:
    """Pinned column bases carry no bending moment."""
    r = solve_monopitch_udl(_SPAN, _EAVES_LOW, _eaves_high(10.0), _W, _SEC, _SEC)
    ref = r["M_eaves_low_Nmm"]  # a representative in-frame moment magnitude
    assert r["M_base_low_Nmm"] == pytest.approx(0.0, abs=1e-3 * ref)
    assert r["M_base_high_Nmm"] == pytest.approx(0.0, abs=1e-3 * ref)


def test_frame_is_asymmetric() -> None:
    """A real slope makes the frame asymmetric — the two eaves moments are not equal."""
    r = solve_monopitch_udl(_SPAN, _EAVES_LOW, _eaves_high(12.0), _W, _SEC, _SEC)
    assert r["M_eaves_low_Nmm"] > 0.0
    assert r["M_eaves_high_Nmm"] > 0.0
    # Different column heights ⇒ different eaves moments (>2% apart for a 12° pitch).
    rel = abs(r["M_eaves_low_Nmm"] - r["M_eaves_high_Nmm"]) / r["M_eaves_low_Nmm"]
    assert rel > 0.02


def test_converges_to_flat_portal_as_slope_vanishes() -> None:
    """As the slope → 0 the mono-pitch solution collapses onto the validated flat portal solver."""
    tiny = _EAVES_LOW + 1.0  # 1 mm rise over a 20 m span ≈ flat
    mono = solve_monopitch_udl(_SPAN, _EAVES_LOW, tiny, _W, _SEC, _SEC)
    flat = solve_portal_udl(_SPAN, _EAVES_LOW, _W, _SEC)
    # Eaves moment and base reactions match the symmetric flat portal to tight tolerance.
    assert mono["M_eaves_low_Nmm"] == pytest.approx(flat["M_eaves_Nmm"], rel=1e-3)
    assert abs(mono["V_low_N"]) == pytest.approx(flat["V_N"], rel=1e-3)
    assert abs(mono["H_low_N"]) == pytest.approx(flat["H_N"], rel=1e-3)
