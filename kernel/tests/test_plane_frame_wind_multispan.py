"""Mechanical-sanity tests for the MULTI-SPAN wind load-combination analysis (v2 inc 2d).

Like ``test_plane_frame_wind.py`` (duopitch) and ``test_plane_frame_wind_monopitch.py``, these
check the wind-on-frame application is *physically* correct — dead-only equivalence to the
validated gravity statics, sway direction, linearity, uplift direction, and that the internal
(valley) columns participate — NOT that the SANS engineering values are right (the registered
engineer's validation). PROVISIONAL (sign-off-pack D13 wind).

Run: PYTHONPATH="kernel/src:tools" pytest kernel/tests/test_plane_frame_wind_multispan.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.analysis.plane_frame import MultiSpanAnalysis
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.sections.library import SectionLibrary

_ZERO = dict(
    rafter_dead_udl_kn_per_m=0.0,
    column_dead_udl_kn_per_m=0.0,
    windward_column_udl_kn_per_m=0.0,
    leeward_column_udl_kn_per_m=0.0,
    windward_rafter_udl_kn_per_m=0.0,
    leeward_rafter_udl_kn_per_m=0.0,
)


def _analysis(n_spans: int = 2) -> MultiSpanAnalysis:
    spec = FrameSpec(
        geometry=FrameGeometry(
            span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0,
            number_of_bays=5, number_of_spans=n_spans,
        ),
        dead=DeadLoadInputs(roof_kpa=0.30),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
    )
    secs = SectionLibrary.load_default().by_increasing_mass()
    return MultiSpanAnalysis(spec, secs[30], secs[25], secs[20])


def _run(msa: MultiSpanAnalysis, **kw: float):
    return msa.run_wind_combination(**{**_ZERO, **kw})


def _disp(msa: MultiSpanAnalysis, **kw: float) -> dict[str, dict[str, float]]:
    return msa.wind_combination_displacements(**{**_ZERO, **kw})


def test_dead_only_combination_reproduces_gravity_statics() -> None:
    msa = _analysis()
    grav = msa.demand(5.0)
    dead_only = _run(msa, rafter_dead_udl_kn_per_m=5.0)
    assert dead_only.rafter_mu_knm == pytest.approx(grav.rafter_mu_knm)
    assert dead_only.ext_col_mu_knm == pytest.approx(grav.ext_col_mu_knm)
    assert dead_only.int_col_cu_kn == pytest.approx(grav.int_col_cu_kn)


def test_no_load_gives_no_demand() -> None:
    d = _run(_analysis())
    assert d.rafter_mu_knm == pytest.approx(0.0, abs=1e-6)
    assert d.ext_col_mu_knm == pytest.approx(0.0, abs=1e-6)


def test_windward_wall_sways_frame_positive_x() -> None:
    # Wind pressure on the windward external column C0 is applied +X -> the frame sways +X.
    d = _disp(_analysis(), windward_column_udl_kn_per_m=5.0)
    assert d["E0"]["DX"] > 0.0
    assert d["E1"]["DX"] > 0.0


def test_horizontal_sway_is_linear() -> None:
    msa = _analysis()
    single = _disp(msa, windward_column_udl_kn_per_m=5.0)["E0"]["DX"]
    double = _disp(msa, windward_column_udl_kn_per_m=10.0)["E0"]["DX"]
    assert double == pytest.approx(2.0 * single)


def test_roof_uplift_lifts_eaves_relative_to_downforce() -> None:
    msa = _analysis()
    uplift = _disp(msa, windward_rafter_udl_kn_per_m=-5.0, leeward_rafter_udl_kn_per_m=-5.0)
    downforce = _disp(msa, windward_rafter_udl_kn_per_m=5.0, leeward_rafter_udl_kn_per_m=5.0)
    assert uplift["E0"]["DY"] > downforce["E0"]["DY"]
    assert uplift["E1"]["DY"] > downforce["E1"]["DY"]


def test_internal_valley_column_participates_under_wind() -> None:
    # A transverse wind case must load the internal (valley) column too (non-zero demand).
    d = _run(
        _analysis(n_spans=3),
        windward_column_udl_kn_per_m=4.0,
        leeward_column_udl_kn_per_m=-1.0,
        windward_rafter_udl_kn_per_m=-3.0,
        leeward_rafter_udl_kn_per_m=-2.0,
    )
    assert d.int_col_cu_kn > 0.0
    assert d.ext_col_mu_knm > 0.0
    assert d.rafter_mu_knm > 0.0
