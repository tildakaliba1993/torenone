"""Task 1.18 — last-mile integration: connections + baseplate + footing + tonnage.

Verifies that design() and check() now produce a COMPLETE single-bay portal frame:
member checks PLUS the eaves/apex connections, the column baseplate, and (when an
allowable bearing pressure is supplied) the pad footing — with steel tonnage — and that
the aggregate passed / governing_utilisation span the whole design.

Run:
    PYTHONPATH="kernel/src:tools" python3 -m pytest kernel/tests/test_last_mile.py -q
"""

from __future__ import annotations

import pytest
from torenone_kernel.design import check, design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FoundationInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import (
    BaseplateDesignResult,
    ConnectionDesignResult,
    PadFootingDesignResult,
    SectionChoice,
)


def _spec(allowable_bearing_kpa: float | None = None) -> FrameSpec:
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
        foundation=FoundationInputs(allowable_bearing_kpa=allowable_bearing_kpa),
    )


# ---------------------------------------------------------------------------
# 1. FrameSpec foundation inputs
# ---------------------------------------------------------------------------


class TestFoundationInputs:
    def test_default_allowable_bearing_is_none(self):
        assert _spec().foundation.allowable_bearing_kpa is None

    def test_default_fcu(self):
        assert _spec().foundation.concrete_fcu_mpa == 25.0

    def test_allowable_bearing_settable(self):
        assert _spec(150.0).foundation.allowable_bearing_kpa == 150.0


# ---------------------------------------------------------------------------
# 2. design() produces the last mile
# ---------------------------------------------------------------------------


class TestDesignLastMile:
    def test_two_connections_eaves_and_apex(self):
        r = design(_spec())
        assert len(r.connections) == 2
        assert {c.location for c in r.connections} == {"eaves", "apex"}
        assert all(isinstance(c, ConnectionDesignResult) for c in r.connections)

    def test_baseplate_present(self):
        r = design(_spec())
        assert isinstance(r.baseplate, BaseplateDesignResult)
        assert r.baseplate.base_fixity == "pinned"

    def test_footing_skipped_without_allowable_bearing(self):
        r = design(_spec())
        assert r.footing is None
        assert any("Pad footing NOT designed" in w for w in r.warnings)

    def test_footing_designed_with_allowable_bearing(self):
        r = design(_spec(allowable_bearing_kpa=150.0))
        assert isinstance(r.footing, PadFootingDesignResult)
        assert r.footing.allowable_bearing_kpa == 150.0
        assert not any("Pad footing NOT designed" in w for w in r.warnings)

    def test_standard_frame_last_mile_passes(self):
        r = design(_spec(allowable_bearing_kpa=150.0))
        assert r.passed
        assert all(c.passed for c in r.connections)
        assert r.baseplate.passed
        assert r.footing is not None and r.footing.passed

    def test_total_steel_tonnes(self):
        r = design(_spec())
        assert r.total_steel_mass_kg is not None
        assert r.total_steel_tonnes == pytest.approx(r.total_steel_mass_kg / 1000.0)

    def test_detail_checks_appended_to_checks(self):
        r = design(_spec(allowable_bearing_kpa=150.0))
        names = [c.name for c in r.checks]
        assert any(n.startswith("connection:") for n in names)
        assert any(n.startswith("baseplate:") for n in names)
        assert any(n.startswith("footing:") for n in names)

    def test_passed_and_governing_span_the_whole_design(self):
        r = design(_spec(allowable_bearing_kpa=150.0))
        # every detail check is included in the aggregate `checks`
        detail_checks = []
        for conn in r.connections:
            detail_checks += conn.checks
        detail_checks += r.baseplate.checks
        detail_checks += r.footing.checks
        for dc in detail_checks:
            assert any(c.name == dc.name and c.utilisation == dc.utilisation for c in r.checks)
        # governing utilisation is the max over the aggregate (incl. details)
        assert r.governing_utilisation == pytest.approx(max(c.utilisation for c in r.checks))


# ---------------------------------------------------------------------------
# 3. check() produces the last mile too
# ---------------------------------------------------------------------------


class TestCheckModeLastMile:
    def _sections(self) -> list[SectionChoice]:
        return [s for s in design(_spec()).sections]

    def test_check_mode_designs_last_mile(self):
        r = check(_spec(allowable_bearing_kpa=150.0), self._sections())
        assert len(r.connections) == 2
        assert r.baseplate is not None
        assert r.footing is not None


# ---------------------------------------------------------------------------
# 4. Determinism (the last mile must be reproducible)
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_design_with_footing_is_deterministic(self):
        a = design(_spec(allowable_bearing_kpa=150.0))
        b = design(_spec(allowable_bearing_kpa=150.0))
        assert a.model_dump(mode="json") == b.model_dump(mode="json")
