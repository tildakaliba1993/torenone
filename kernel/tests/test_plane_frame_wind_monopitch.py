"""Mechanical-sanity tests for the MONO-PITCH wind load-combination analysis (v2 inc 2).

Like ``test_plane_frame_wind.py`` (duopitch), these check the wind-on-frame application is
*physically* correct — equilibrium via dead-only equivalence to the validated gravity statics,
sway direction, linearity, and uplift direction — NOT that the SANS engineering values are right
(that is the registered engineer's validation against worked examples). The method is PROVISIONAL
(sign-off-pack D12 wind) for exactly that reason.

Run: PYTHONPATH="kernel/src:tools" pytest kernel/tests/test_plane_frame_wind_monopitch.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.analysis.plane_frame import MonopitchAnalysis
from torenone_kernel.models.enums import RoofType, TerrainCategory
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
    low_column_wind_udl_kn_per_m=0.0,
    high_column_wind_udl_kn_per_m=0.0,
    rafter_wind_udl_kn_per_m=0.0,
)


def _analysis() -> MonopitchAnalysis:
    spec = FrameSpec(
        geometry=FrameGeometry(
            span_m=18.0, eaves_height_m=4.0, roof_pitch_deg=8.0, bay_spacing_m=6.0,
            number_of_bays=4, roof_type=RoofType.MONOPITCH,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )
    secs = SectionLibrary.load_default().by_increasing_mass()
    return MonopitchAnalysis(spec, column_section=secs[30], rafter_section=secs[20])


def _run(mp: MonopitchAnalysis, **kw: float):
    return mp.run_wind_combination(**{**_ZERO, **kw})


def _disp(mp: MonopitchAnalysis, **kw: float) -> dict[str, dict[str, float]]:
    return mp.wind_combination_displacements(**{**_ZERO, **kw})


def test_dead_only_combination_reproduces_gravity_statics() -> None:
    # A wind combination with ONLY the dead rafter UDL must equal the validated gravity demand()
    # for the same UDL (same model, same load) — equilibrium sanity on the new wind model.
    mp = _analysis()
    grav = mp.demand(5.0)
    dead_only = _run(mp, rafter_dead_udl_kn_per_m=5.0)
    assert dead_only.rafter_mu_knm == pytest.approx(grav.rafter_mu_knm)
    assert dead_only.low_col_mu_knm == pytest.approx(grav.low_col_mu_knm)
    assert dead_only.high_col_mu_knm == pytest.approx(grav.high_col_mu_knm)


def test_no_load_gives_no_demand() -> None:
    d = _run(_analysis())
    assert d.rafter_mu_knm == pytest.approx(0.0, abs=1e-6)
    assert d.low_col_mu_knm == pytest.approx(0.0, abs=1e-6)
    assert d.high_col_mu_knm == pytest.approx(0.0, abs=1e-6)


def test_low_column_pressure_sways_frame_positive_x() -> None:
    # Wind pressure on the low (left) column is applied +X -> the frame sways in +X.
    d = _disp(_analysis(), low_column_wind_udl_kn_per_m=5.0)
    assert d["EL"]["DX"] > 0.0
    assert d["EH"]["DX"] > 0.0


def test_high_column_pressure_sways_frame_negative_x() -> None:
    # Wind pressure on the high (right) column is applied -X -> the frame sways in -X.
    d = _disp(_analysis(), high_column_wind_udl_kn_per_m=5.0)
    assert d["EL"]["DX"] < 0.0
    assert d["EH"]["DX"] < 0.0


def test_horizontal_sway_is_linear() -> None:
    mp = _analysis()
    single = _disp(mp, low_column_wind_udl_kn_per_m=5.0)["EL"]["DX"]
    double = _disp(mp, low_column_wind_udl_kn_per_m=10.0)["EL"]["DX"]
    assert double == pytest.approx(2.0 * single)


def test_roof_uplift_lifts_eaves_relative_to_downforce() -> None:
    # By the sign convention, a NEGATIVE rafter UDL is uplift (roof pushed up), a positive one is
    # downforce. Uplift must raise the eaves relative to an equal-magnitude downforce.
    mp = _analysis()
    uplift = _disp(mp, rafter_wind_udl_kn_per_m=-5.0)
    downforce = _disp(mp, rafter_wind_udl_kn_per_m=5.0)
    assert uplift["EL"]["DY"] > downforce["EL"]["DY"]
    assert uplift["EH"]["DY"] > downforce["EH"]["DY"]


def test_wind_produces_member_moments() -> None:
    # A transverse wind case (columns + roof) must induce non-trivial member moments.
    d = _run(
        _analysis(),
        low_column_wind_udl_kn_per_m=4.0,
        high_column_wind_udl_kn_per_m=-2.0,
        rafter_wind_udl_kn_per_m=-3.0,
    )
    assert d.low_col_mu_knm > 0.0
    assert d.rafter_mu_knm > 0.0
