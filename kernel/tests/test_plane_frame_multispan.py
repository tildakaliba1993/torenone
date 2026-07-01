"""Validation of the multi-span (internal-column) portal statics — Path B (PROVISIONAL).

The new geometry's foundation, validated hard *before* anything sizes members on it. We check the
conditions a correct pinned-base multi-span solution MUST satisfy:

  1. Global equilibrium — vertical reactions carry the total applied vertical load; horizontal
     reactions sum to zero (no applied horizontal load).
  2. Symmetry — a symmetric multi-span under uniform gravity has mirror-symmetric vertical reactions
     and mirror-antisymmetric horizontal reactions (interior column of an odd layout → ~0 thrust).
  3. Load share — an internal (valley) column supports two half-spans, so it carries ≈ 2× an
     external column.
  4. Convergence — a single flat span collapses onto the validated flat portal solver
     `solve_portal_udl`.

PROVISIONAL: the multi-span method awaits registered-engineer validation before go-live.
Run: PYTHONPATH="kernel/src:tools" pytest kernel/tests/test_plane_frame_multispan.py -q
"""

from __future__ import annotations

import math

import pytest
from torenone_kernel.analysis.plane_frame import solve_multispan_udl, solve_portal_udl
from torenone_kernel.sections import SectionLibrary

_LIB = SectionLibrary.load_default()
_SEC = _LIB.get("356x171x51")

_SPAN = 20_000.0   # mm (per span)
_EAVES = 6_000.0   # mm
_W = 5.0           # N/mm (= 5 kN/m) downward on each rafter


def _apex(pitch_deg: float) -> float:
    return _EAVES + (_SPAN / 2.0) * math.tan(math.radians(pitch_deg))


def _solve(n_spans: int, pitch_deg: float = 10.0):
    return solve_multispan_udl(_SPAN, _EAVES, _apex(pitch_deg), n_spans, _W, _SEC, _SEC, _SEC)


def test_vertical_equilibrium() -> None:
    r = _solve(2)
    assert r.sum_V_N == pytest.approx(r.total_vertical_N, rel=1e-4)


def test_horizontal_equilibrium() -> None:
    r = _solve(2)
    assert r.sum_H_N == pytest.approx(0.0, abs=1e-6 * r.total_vertical_N)


def test_two_span_symmetry() -> None:
    r = _solve(2)  # bases: [ext, int, ext]
    assert len(r.V_N) == 3
    assert r.V_N[0] == pytest.approx(r.V_N[2], rel=1e-4)          # mirror vertical
    assert r.H_N[0] == pytest.approx(-r.H_N[2], abs=1e-4 * r.total_vertical_N)  # opposing thrust
    assert r.H_N[1] == pytest.approx(0.0, abs=1e-4 * r.total_vertical_N)        # centre no thrust


def test_internal_column_carries_about_double() -> None:
    r = _solve(2)
    assert r.V_N[1] > r.V_N[0]  # the valley column takes two half-spans
    assert r.V_N[1] == pytest.approx(2.0 * r.V_N[0], rel=0.2)


def test_three_span_equilibrium_and_symmetry() -> None:
    r = _solve(3)  # bases: [ext, int, int, ext]
    assert len(r.V_N) == 4
    assert r.sum_V_N == pytest.approx(r.total_vertical_N, rel=1e-4)
    assert r.V_N[0] == pytest.approx(r.V_N[3], rel=1e-4)
    assert r.V_N[1] == pytest.approx(r.V_N[2], rel=1e-4)


def test_converges_to_flat_portal() -> None:
    """A single flat (zero-pitch) span reproduces the validated flat portal eaves moment."""
    ms = solve_multispan_udl(_SPAN, _EAVES, _EAVES, 1, _W, _SEC, _SEC, _SEC)
    portal = solve_portal_udl(_SPAN, _EAVES, _W, _SEC)
    assert ms.M_eaves_ext_Nmm == pytest.approx(portal["M_eaves_Nmm"], rel=1e-3)
    assert ms.M_eaves_int_Nmm is None  # a single span has no internal eaves


def test_single_span_equilibrium() -> None:
    r = _solve(1)
    assert r.sum_V_N == pytest.approx(r.total_vertical_N, rel=1e-4)
    assert r.sum_H_N == pytest.approx(0.0, abs=1e-6 * r.total_vertical_N)
