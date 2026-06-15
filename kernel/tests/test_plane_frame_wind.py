"""Mechanical-sanity tests for the wind load-combination analysis (Part B).

These check the wind-on-frame application is *physically* correct (equilibrium,
uplift direction, asymmetric loading) — NOT that the SANS engineering values are
right (that is the co-founder's validation, against worked examples). The method
is flagged PROVISIONAL for exactly that reason.
"""

from __future__ import annotations

from torenone_kernel.analysis.plane_frame import PortalAnalysis
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import MemberForces
from torenone_kernel.sections.library import SectionLibrary


def _analysis() -> PortalAnalysis:
    spec = FrameSpec(
        geometry=FrameGeometry(
            span_m=20, eaves_height_m=6, roof_pitch_deg=10, bay_spacing_m=6, number_of_bays=5
        ),
        dead=DeadLoadInputs(roof_kpa=0.15),
        wind=WindContext(basic_wind_speed_ms=36, terrain_category=TerrainCategory.B),
    )
    secs = SectionLibrary.load_default().by_increasing_mass()
    return PortalAnalysis(spec, column_section=secs[30], rafter_section=secs[20])


def _by_loc(result) -> dict[str, MemberForces]:
    return {f.location: f for f in result.forces}


def _wind(pa: PortalAnalysis, **kw) -> dict[str, MemberForces]:
    base = dict(
        rafter_dead_udl_kn_per_m=0.0,
        column_dead_udl_kn_per_m=0.0,
        windward_column_udl_kn_per_m=0.0,
        leeward_column_udl_kn_per_m=0.0,
        windward_rafter_udl_kn_per_m=0.0,
        leeward_rafter_udl_kn_per_m=0.0,
    )
    base.update(kw)
    return _by_loc(pa.run_wind_combination("test", **base))


class TestWindAnalysisMechanics:
    def test_gravity_only_matches_the_tested_run_path(self) -> None:
        # Same loading via run() and run_wind_combination() must give the same forces.
        pa = _analysis()
        w = 5.0
        grav = _by_loc(pa.run("ULS-1", w, 0.0))
        wind = _wind(pa, rafter_dead_udl_kn_per_m=w)
        assert abs(grav["apex"].moment_knm - wind["apex"].moment_knm) < 1e-6
        assert abs(grav["eaves_L"].moment_knm - wind["eaves_L"].moment_knm) < 1e-6
        assert abs(grav["col_base_L"].axial_kn - wind["col_base_L"].axial_kn) < 1e-6

    def test_horizontal_wind_bends_the_columns_and_reacts(self) -> None:
        # Pressure on the windward column alone must bend the columns and produce a
        # horizontal base reaction (an unloaded frame has ~0 of both).
        r = _wind(_analysis(), windward_column_udl_kn_per_m=3.0)
        assert abs(r["eaves_L"].moment_knm) > 1.0
        assert abs(r["col_base_L"].shear_kn) > 0.1

    def test_roof_uplift_reduces_column_compression(self) -> None:
        # Uplift (−ve rafter normal load) removes gravity → less column axial compression.
        pa = _analysis()
        dead_only = _wind(pa, rafter_dead_udl_kn_per_m=5.0)
        with_uplift = _wind(
            pa,
            rafter_dead_udl_kn_per_m=5.0,
            windward_rafter_udl_kn_per_m=-4.0,
            leeward_rafter_udl_kn_per_m=-4.0,
        )
        assert abs(with_uplift["col_base_L"].axial_kn) < abs(dead_only["col_base_L"].axial_kn)

    def test_asymmetric_wind_loads_the_two_columns_differently(self) -> None:
        # Windward pressure + leeward suction is asymmetric → the columns must differ
        # (this is why the symmetric gravity heuristics can't be reused for wind).
        r = _wind(
            _analysis(),
            windward_column_udl_kn_per_m=3.0,
            leeward_column_udl_kn_per_m=-1.5,
        )
        assert abs(r["eaves_L"].moment_knm - r["eaves_R"].moment_knm) > 0.5


class TestWindDisplacements:
    """`wind_combination_displacements` — used by the SLS-2 eaves-sway check."""

    def test_pinned_bases_do_not_translate(self) -> None:
        # Pinned supports restrain DX/DY → both base nodes stay put under any wind.
        disp = _analysis().wind_combination_displacements(
            rafter_dead_udl_kn_per_m=2.0,
            column_dead_udl_kn_per_m=1.0,
            windward_column_udl_kn_per_m=3.0,
            leeward_column_udl_kn_per_m=-1.5,
            windward_rafter_udl_kn_per_m=0.0,
            leeward_rafter_udl_kn_per_m=0.0,
        )
        assert abs(disp["BL"]["DX"]) < 1e-6
        assert abs(disp["BR"]["DX"]) < 1e-6

    def test_transverse_wind_drifts_the_eaves(self) -> None:
        # Horizontal pressure on the windward column produces lateral eaves drift; an
        # unloaded frame produces ~none. (Magnitude is PROVISIONAL — sign-convention
        # validation is the co-founder's; this only asserts the model responds.)
        pa = _analysis()
        drift = abs(
            pa.wind_combination_displacements(
                rafter_dead_udl_kn_per_m=0.0,
                column_dead_udl_kn_per_m=0.0,
                windward_column_udl_kn_per_m=3.0,
                leeward_column_udl_kn_per_m=0.0,
                windward_rafter_udl_kn_per_m=0.0,
                leeward_rafter_udl_kn_per_m=0.0,
            )["EL"]["DX"]
        )
        assert drift > 0.1

    def test_displacements_match_force_model_path(self) -> None:
        # The displacement path and the force path must build the SAME model: a pure
        # gravity rafter load gives a symmetric, downward apex with zero net eaves sway.
        pa = _analysis()
        disp = pa.wind_combination_displacements(
            rafter_dead_udl_kn_per_m=5.0,
            column_dead_udl_kn_per_m=0.0,
            windward_column_udl_kn_per_m=0.0,
            leeward_column_udl_kn_per_m=0.0,
            windward_rafter_udl_kn_per_m=0.0,
            leeward_rafter_udl_kn_per_m=0.0,
        )
        assert disp["AP"]["DY"] < 0.0  # apex deflects downward under gravity
        assert abs(disp["EL"]["DX"] + disp["ER"]["DX"]) < 1e-6  # symmetric: equal & opposite
