"""Task 3.2 — spec-parsing tests.

Covers the deliverable: sample descriptions -> expected specs, and missing-field
cases flagged (never silently guessed — PRD FR-2).

The OpenAI call is exercised with a fake client (no network / key). The
deterministic extraction->FrameSpec mapping is tested directly.

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_parsing.py -q
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from torenone_ai.parsing import (
    SYSTEM_PROMPT,
    Assumption,
    FrameSpecExtraction,
    MissingField,
    ParseResult,
    build_frame_spec,
    parse_description,
)
from torenone_kernel.models.enums import BaseFixity, SteelGrade, TerrainCategory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _complete_extraction(**overrides: Any) -> FrameSpecExtraction:
    """A fully-specified extraction (all 8 required fields present)."""
    base: dict[str, Any] = dict(
        span_m=15.0,
        eaves_height_m=5.0,
        roof_pitch_deg=8.0,
        bay_spacing_m=6.0,
        number_of_bays=5,
        roof_dead_load_kpa=0.20,
        basic_wind_speed_ms=36.0,
        terrain_category=TerrainCategory.B,
    )
    base.update(overrides)
    return FrameSpecExtraction(**base)


class _FakeResponses:
    def __init__(self, parsed: Any, capture: dict[str, Any]) -> None:
        self._parsed = parsed
        self._capture = capture

    def parse(self, **kwargs: Any) -> Any:
        self._capture.update(kwargs)
        return SimpleNamespace(output_parsed=self._parsed)


class _FakeClient:
    """Stand-in for openai.OpenAI — records the parse() call and returns a canned result."""

    def __init__(self, parsed: Any) -> None:
        self.capture: dict[str, Any] = {}
        self.responses = _FakeResponses(parsed, self.capture)


# ---------------------------------------------------------------------------
# 1. Extraction model — all fields nullable (null = "not stated")
# ---------------------------------------------------------------------------


class TestExtractionModel:
    def test_all_fields_default_to_none(self):
        x = FrameSpecExtraction()
        for name in FrameSpecExtraction.model_fields:
            assert getattr(x, name) is None, f"{name} should default to None"

    def test_usable_as_structured_output_schema(self):
        """Must be expressible as a JSON schema (OpenAI Structured Outputs target)."""
        schema = FrameSpecExtraction.model_json_schema()
        assert schema["type"] == "object"
        assert "span_m" in schema["properties"]
        assert "terrain_category" in schema["properties"]


# ---------------------------------------------------------------------------
# 2. Complete description -> valid FrameSpec
# ---------------------------------------------------------------------------


class TestCompleteBuild:
    def test_complete_extraction_is_complete(self):
        result = build_frame_spec(_complete_extraction())
        assert result.is_complete
        assert result.spec is not None
        assert not result.missing
        assert not result.errors

    def test_required_values_mapped(self):
        spec = build_frame_spec(_complete_extraction()).spec
        assert spec is not None
        assert spec.geometry.span_m == 15.0
        assert spec.geometry.eaves_height_m == 5.0
        assert spec.geometry.roof_pitch_deg == 8.0
        assert spec.geometry.bay_spacing_m == 6.0
        assert spec.geometry.number_of_bays == 5
        assert spec.dead.roof_kpa == 0.20
        assert spec.wind.basic_wind_speed_ms == 36.0
        assert spec.wind.terrain_category == TerrainCategory.B

    def test_not_needs_clarification(self):
        assert build_frame_spec(_complete_extraction()).needs_clarification is False


# ---------------------------------------------------------------------------
# 3. Missing required fields are FLAGGED, never guessed (FR-2)
# ---------------------------------------------------------------------------


class TestMissingFlagged:
    def test_empty_extraction_flags_all_required(self):
        result = build_frame_spec(FrameSpecExtraction())
        assert result.spec is None
        assert result.needs_clarification
        flagged = {m.field for m in result.missing}
        assert flagged == {
            "geometry.span_m",
            "geometry.eaves_height_m",
            "geometry.roof_pitch_deg",
            "geometry.bay_spacing_m",
            "geometry.number_of_bays",
            "dead.roof_kpa",
            "wind.basic_wind_speed_ms",
            "wind.terrain_category",
        }

    def test_single_missing_field_flagged(self):
        result = build_frame_spec(_complete_extraction(span_m=None))
        assert result.spec is None
        assert [m.field for m in result.missing] == ["geometry.span_m"]

    def test_missing_terrain_flagged_not_guessed(self):
        """Terrain is required and must be flagged, not defaulted to a category."""
        result = build_frame_spec(_complete_extraction(terrain_category=None))
        assert result.spec is None
        assert any(m.field == "wind.terrain_category" for m in result.missing)

    def test_missing_field_has_human_label_and_reason(self):
        m = build_frame_spec(_complete_extraction(bay_spacing_m=None)).missing[0]
        assert isinstance(m, MissingField)
        assert m.label == "bay spacing (m)"
        assert m.why  # non-empty justification

    def test_missing_blocks_defaults(self):
        """If required fields are missing, we don't bother computing assumptions."""
        result = build_frame_spec(FrameSpecExtraction())
        assert result.assumptions == []


# ---------------------------------------------------------------------------
# 4. Documented defaults applied AND recorded as assumptions
# ---------------------------------------------------------------------------


class TestDefaultsAsAssumptions:
    def test_defaults_applied_to_spec(self):
        spec = build_frame_spec(_complete_extraction()).spec
        assert spec is not None
        assert spec.dead.services_kpa == 0.0
        assert spec.dead.wall_cladding_kpa == 0.0
        assert spec.imposed.roof_access is False
        assert spec.wind.site_altitude_m == 0.0
        assert spec.wind.has_dominant_opening is False
        assert spec.materials.steel_grade == SteelGrade.S355JR
        assert spec.base_fixity == BaseFixity.PINNED
        assert spec.restraints.rafter_restraint_spacing_m is None
        assert spec.restraints.column_restraint_spacing_m is None

    def test_every_default_is_recorded_as_assumption(self):
        result = build_frame_spec(_complete_extraction())
        fields = {a.field for a in result.assumptions}
        assert {
            "dead.services_kpa",
            "dead.wall_cladding_kpa",
            "imposed.roof_access",
            "wind.site_altitude_m",
            "wind.has_dominant_opening",
            "materials.steel_grade",
            "base_fixity",
            "restraints.rafter_restraint_spacing_m",
            "restraints.column_restraint_spacing_m",
        } <= fields

    def test_assumption_carries_value_and_note(self):
        result = build_frame_spec(_complete_extraction())
        steel = next(a for a in result.assumptions if a.field == "materials.steel_grade")
        assert isinstance(steel, Assumption)
        assert steel.value == SteelGrade.S355JR
        assert "S355JR" in steel.note

    def test_stated_optional_value_is_not_assumed(self):
        """If the user states an optional value, it is used and NOT recorded as assumed."""
        result = build_frame_spec(
            _complete_extraction(steel_grade=SteelGrade.S275JR, services_kpa=0.10)
        )
        assert result.spec is not None
        assert result.spec.materials.steel_grade == SteelGrade.S275JR
        assert result.spec.dead.services_kpa == 0.10
        assumed_fields = {a.field for a in result.assumptions}
        assert "materials.steel_grade" not in assumed_fields
        assert "dead.services_kpa" not in assumed_fields

    def test_restraints_unrestrained_is_flagged_as_assumption(self):
        result = build_frame_spec(_complete_extraction())
        raf = next(
            a for a in result.assumptions
            if a.field == "restraints.rafter_restraint_spacing_m"
        )
        assert raf.value is None
        assert "unrestrained" in raf.note.lower()


# ---------------------------------------------------------------------------
# 5. Stated-but-invalid values surface as errors (not a silent bad spec)
# ---------------------------------------------------------------------------


class TestValidationErrors:
    def test_pitch_over_45_is_error(self):
        result = build_frame_spec(_complete_extraction(roof_pitch_deg=60.0))
        assert result.spec is None
        assert result.errors
        assert any("roof_pitch_deg" in e for e in result.errors)

    def test_negative_span_is_error(self):
        result = build_frame_spec(_complete_extraction(span_m=-3.0))
        assert result.spec is None
        assert result.errors

    def test_zero_bays_is_error(self):
        result = build_frame_spec(_complete_extraction(number_of_bays=0))
        assert result.spec is None
        assert result.errors

    def test_invalid_is_not_complete(self):
        assert build_frame_spec(_complete_extraction(roof_pitch_deg=90.0)).is_complete is False


# ---------------------------------------------------------------------------
# 6. parse_description — OpenAI wiring (fake client, no network)
# ---------------------------------------------------------------------------


class TestParseDescription:
    def test_maps_parsed_extraction_to_result(self):
        client = _FakeClient(_complete_extraction())
        result = parse_description("a 15 m span shed", client=client, model="gpt-5.5")
        assert isinstance(result, ParseResult)
        assert result.is_complete
        assert result.spec is not None and result.spec.geometry.span_m == 15.0

    def test_passes_model_and_text_format(self):
        client = _FakeClient(_complete_extraction())
        parse_description("desc", client=client, model="gpt-5.5")
        assert client.capture["model"] == "gpt-5.5"
        assert client.capture["text_format"] is FrameSpecExtraction

    def test_user_text_forwarded_to_model(self):
        client = _FakeClient(_complete_extraction())
        parse_description("a 20 metre warehouse", client=client, model="gpt-5.5")
        msgs = client.capture["input"]
        assert any(m["role"] == "user" and "20 metre warehouse" in m["content"] for m in msgs)
        assert any(m["role"] == "system" for m in msgs)

    def test_partial_extraction_flags_missing(self):
        client = _FakeClient(_complete_extraction(terrain_category=None, span_m=None))
        result = parse_description("partial", client=client, model="gpt-5.5")
        assert result.needs_clarification
        flagged = {m.field for m in result.missing}
        assert {"geometry.span_m", "wind.terrain_category"} <= flagged

    def test_none_output_parsed_does_not_fabricate(self):
        """If the model returns nothing parseable, flag — never invent a spec."""
        client = _FakeClient(None)
        result = parse_description("gibberish", client=client, model="gpt-5.5")
        assert result.spec is None
        assert result.missing  # everything flagged
        assert result.errors


# ---------------------------------------------------------------------------
# 7. System prompt enforces the no-guess contract (FR-2)
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_prompt_forbids_guessing(self):
        lowered = SYSTEM_PROMPT.lower()
        assert "null" in lowered
        assert "never guess" in lowered or "never guess, infer" in lowered

    def test_prompt_forbids_calculation(self):
        assert "calculation" in SYSTEM_PROMPT.lower() or "calculate" in SYSTEM_PROMPT.lower()

    def test_prompt_prefers_question_over_guess(self):
        assert "clarifying question" in SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# 8. Determinism — same extraction always maps to the same spec/fingerprint
# ---------------------------------------------------------------------------


class TestDeterministicMapping:
    def test_same_extraction_same_spec(self):
        a = build_frame_spec(_complete_extraction()).spec
        b = build_frame_spec(_complete_extraction()).spec
        assert a is not None and b is not None
        assert a.model_dump(mode="json") == b.model_dump(mode="json")

    @pytest.mark.parametrize("field", ["span_m", "eaves_height_m", "roof_dead_load_kpa"])
    def test_different_input_changes_spec(self, field: str):
        base = build_frame_spec(_complete_extraction()).spec
        changed = build_frame_spec(_complete_extraction(**{field: 99.0})).spec
        assert base is not None and changed is not None
        assert base.model_dump(mode="json") != changed.model_dump(mode="json")
