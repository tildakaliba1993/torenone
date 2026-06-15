"""Task 1.13 — Determinism & reproducibility tests.

Core guarantee: design(spec) produces byte-identical DesignResult for every call
with the same FrameSpec and the same pinned rule-set version. This underpins:
    - PRD NFR-3 (auditability): the calc-package must be reproducible.
    - PRD FR-20 (rules_version): every result must embed the standard editions used.
    - The validation gate (Phase 8): results must match the registered-engineer's
      reference output produced from the same inputs.

Tests cover:
    1. Two calls on the same spec → model_dump() is identical (byte-equal).
    2. Several different frame configurations all satisfy the determinism invariant.
    3. JSON round-trip: serialize → deserialize → compare with original.
    4. rules_version is fully populated with all expected standard identifiers.
    5. Changing any input field changes the output (no inadvertent caching).
"""

from __future__ import annotations

import json

import pytest
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    Restraints,
    WindContext,
)
from torenone_kernel.rules_version import as_dict as rules_version_dict

# ---------------------------------------------------------------------------
# Shared fixtures — span the realistic South African industrial portal range
# ---------------------------------------------------------------------------

def _spec_standard() -> FrameSpec:
    """15 m span, 5 m eaves, 8° pitch, 6 m bays — the baseline test frame."""
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )


def _spec_wider() -> FrameSpec:
    """20 m span, 6 m eaves, 5° pitch — wider frame tests different convergence path."""
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=5.0,
            bay_spacing_m=5.0, number_of_bays=4,
        ),
        dead=DeadLoadInputs(roof_kpa=0.15, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=32.0, terrain_category=TerrainCategory.C),
    )


def _spec_restrained() -> FrameSpec:
    """12 m span with explicit purlin/girt restraints — tests LTB unbraced-length branch."""
    return FrameSpec(
        geometry=FrameGeometry(
            span_m=12.0, eaves_height_m=4.5, roof_pitch_deg=10.0,
            bay_spacing_m=5.0, number_of_bays=6,
        ),
        dead=DeadLoadInputs(roof_kpa=0.25, services_kpa=0.10),
        wind=WindContext(basic_wind_speed_ms=40.0, terrain_category=TerrainCategory.B),
        restraints=Restraints(
            rafter_restraint_spacing_m=1.8,
            column_restraint_spacing_m=2.0,
        ),
    )


_ALL_SPECS = [
    pytest.param(_spec_standard,  id="standard-15m"),
    pytest.param(_spec_wider,     id="wider-20m"),
    pytest.param(_spec_restrained, id="restrained-12m"),
]


# ---------------------------------------------------------------------------
# 1.  Identical output on repeated calls
# ---------------------------------------------------------------------------

def _json_dump(result) -> dict:
    """Serialise DesignResult to a pure-JSON dict (enums→str, tuples→list).

    This is the canonical comparison form for determinism tests — it matches
    exactly what would be persisted to a database or audit store (PRD NFR-3).
    """
    return json.loads(json.dumps(result.model_dump(mode="json")))


class TestRepeatabilityPerSpec:
    @pytest.mark.parametrize("spec_factory", _ALL_SPECS)
    def test_two_calls_produce_identical_model_dump(self, spec_factory):
        """design() is a pure function: same spec → byte-equal JSON-serialised output."""
        spec = spec_factory()
        r1 = design(spec)
        r2 = design(spec)
        d1, d2 = _json_dump(r1), _json_dump(r2)
        assert d1 == d2, (
            f"design() non-deterministic for {spec_factory.__name__!r}:\n"
            f"  call-1 sections: {[(s.member, s.designation) for s in r1.sections]}\n"
            f"  call-2 sections: {[(s.member, s.designation) for s in r2.sections]}"
        )

    @pytest.mark.parametrize("spec_factory", _ALL_SPECS)
    def test_two_calls_produce_identical_passed_flag(self, spec_factory):
        spec = spec_factory()
        assert design(spec).passed == design(spec).passed

    @pytest.mark.parametrize("spec_factory", _ALL_SPECS)
    def test_two_calls_produce_identical_governing_utilisation(self, spec_factory):
        spec = spec_factory()
        r1 = design(spec)
        r2 = design(spec)
        assert r1.governing_utilisation == pytest.approx(r2.governing_utilisation, rel=1e-12)

    @pytest.mark.parametrize("spec_factory", _ALL_SPECS)
    def test_json_string_is_byte_identical(self, spec_factory):
        """json.dumps with sorted keys produces byte-identical strings — the strongest
        determinism guarantee, suitable for checksumming or content-addressed storage."""
        spec = spec_factory()
        s1 = json.dumps(_json_dump(design(spec)), sort_keys=True)
        s2 = json.dumps(_json_dump(design(spec)), sort_keys=True)
        assert s1 == s2


# ---------------------------------------------------------------------------
# 2.  JSON round-trip (PRD NFR-3 — result must be persistable + reloadable)
# ---------------------------------------------------------------------------

class TestJsonRoundTrip:
    @pytest.mark.parametrize("spec_factory", _ALL_SPECS)
    def test_model_dump_mode_json_is_serialisable(self, spec_factory):
        """model_dump(mode='json') produces only JSON primitives — required for audit storage."""
        r = design(spec_factory())
        # Will raise TypeError if any value is not JSON-compatible
        payload = json.dumps(r.model_dump(mode="json"))
        assert len(payload) > 0

    @pytest.mark.parametrize("spec_factory", _ALL_SPECS)
    def test_json_round_trip_is_lossless(self, spec_factory):
        """model_dump(mode='json') → json.dumps() → json.loads() is lossless.

        mode='json' serialises enums to their string values and tuples to lists,
        so the round-trip dict equals the input dict exactly.
        """
        r = design(spec_factory())
        d = r.model_dump(mode="json")
        assert d == json.loads(json.dumps(d)), (
            "JSON round-trip lost or mutated data — result cannot be durably stored"
        )


# ---------------------------------------------------------------------------
# 3.  rules_version completeness (PRD FR-20)
# ---------------------------------------------------------------------------

class TestRulesVersion:
    _REQUIRED_KEYS = {
        "SANS 10160-1",   # load combinations (2011 final — verified)
        "SANS 10160-2",   # imposed loads
        "SANS 10160-3",   # wind actions
        "SANS 10162-1",   # steel design
        "section_data",   # SAISC section library provenance
    }

    def test_rules_version_contains_all_required_keys(self):
        """Every standard edition used in the kernel must appear in rules_version."""
        r = design(_spec_standard())
        missing = self._REQUIRED_KEYS - set(r.rules_version.keys())
        assert not missing, (
            f"rules_version is missing edition entries for: {missing}. "
            "These must be cited for auditability (PRD FR-20)."
        )

    def test_rules_version_values_are_non_empty(self):
        r = design(_spec_standard())
        empty = [k for k, v in r.rules_version.items() if not v.strip()]
        assert not empty, f"rules_version has empty values for keys: {empty}"

    def test_rules_version_module_as_dict_consistent_with_result(self):
        """The rules_version embedded in DesignResult must match rules_version.as_dict()."""
        r = design(_spec_standard())
        assert r.rules_version == rules_version_dict()

    def test_rules_version_is_identical_across_calls(self):
        spec = _spec_standard()
        r1 = design(spec)
        r2 = design(spec)
        assert r1.rules_version == r2.rules_version


# ---------------------------------------------------------------------------
# 4.  Input sensitivity — different spec → different output
# ---------------------------------------------------------------------------

class TestInputSensitivity:
    """Ensure changes to spec parameters propagate to the result.

    This rules out any hidden global caching that would make determinism trivially
    true (because the result is always the same regardless of input).
    """

    def test_wider_span_gives_different_result_than_standard(self):
        r_a = design(_spec_standard())
        r_b = design(_spec_wider())
        assert _json_dump(r_a) != _json_dump(r_b)

    def test_restrained_spec_gives_different_result_than_standard(self):
        r_a = design(_spec_standard())
        r_c = design(_spec_restrained())
        assert _json_dump(r_a) != _json_dump(r_c)

    def test_heavier_dead_load_changes_result(self):
        spec_a = _spec_standard()
        spec_b = FrameSpec(
            geometry=spec_a.geometry,
            dead=DeadLoadInputs(roof_kpa=0.60, services_kpa=0.20),  # 3× heavier
            wind=spec_a.wind,
        )
        assert _json_dump(design(spec_a)) != _json_dump(design(spec_b))

    def test_different_terrain_category_changes_result(self):
        """Terrain category affects wind loads (qp) which affect the sway check."""
        spec_a = _spec_standard()
        spec_b = FrameSpec(
            geometry=spec_a.geometry,
            dead=spec_a.dead,
            wind=WindContext(
                basic_wind_speed_ms=spec_a.wind.basic_wind_speed_ms,
                terrain_category=TerrainCategory.D,  # urban vs open country
                site_altitude_m=spec_a.wind.site_altitude_m,
            ),
        )
        assert _json_dump(design(spec_a)) != _json_dump(design(spec_b))
