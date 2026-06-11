"""Task 3.3 — clarifying-question tests.

Covers the deliverable: when input is ambiguous/incomplete, the system returns a
question, not a guess (PRD FR-2).

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_clarify.py -q
"""

from __future__ import annotations

from typing import Any

from torenone_ai.clarify import (
    ClarifyingQuestion,
    clarification_prompt,
    clarifying_questions,
)
from torenone_ai.parsing import FrameSpecExtraction, build_frame_spec
from torenone_kernel.models.enums import TerrainCategory

_REQUIRED_PATHS = {
    "geometry.span_m",
    "geometry.eaves_height_m",
    "geometry.roof_pitch_deg",
    "geometry.bay_spacing_m",
    "geometry.number_of_bays",
    "dead.roof_kpa",
    "wind.basic_wind_speed_ms",
    "wind.terrain_category",
}


def _complete(**overrides: Any) -> FrameSpecExtraction:
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


# ---------------------------------------------------------------------------
# 1. Complete result -> no questions
# ---------------------------------------------------------------------------


class TestNoQuestionsWhenComplete:
    def test_complete_has_no_questions(self):
        result = build_frame_spec(_complete())
        assert clarifying_questions(result) == []

    def test_complete_prompt_is_none(self):
        result = build_frame_spec(_complete())
        assert clarification_prompt(result) is None


# ---------------------------------------------------------------------------
# 2. Missing fields -> a question per field (ask, never guess)
# ---------------------------------------------------------------------------


class TestQuestionsForMissing:
    def test_all_missing_yields_question_per_required_field(self):
        result = build_frame_spec(FrameSpecExtraction())
        qs = clarifying_questions(result)
        assert {q.field for q in qs} == _REQUIRED_PATHS
        assert all(q.kind == "missing" for q in qs)

    def test_every_question_has_text(self):
        qs = clarifying_questions(build_frame_spec(FrameSpecExtraction()))
        assert all("?" in q.question for q in qs)
        assert all(len(q.question) > 10 for q in qs)

    def test_single_missing_one_question(self):
        result = build_frame_spec(_complete(span_m=None))
        qs = clarifying_questions(result)
        assert len(qs) == 1
        assert qs[0].field == "geometry.span_m"
        assert qs[0].kind == "missing"

    def test_span_question_has_metre_unit(self):
        qs = clarifying_questions(build_frame_spec(_complete(span_m=None)))
        assert qs[0].unit == "m"

    def test_terrain_question_offers_enum_options(self):
        qs = clarifying_questions(build_frame_spec(_complete(terrain_category=None)))
        terrain = next(q for q in qs if q.field == "wind.terrain_category")
        assert terrain.options == ["A", "B", "C", "D"]

    def test_number_of_bays_has_no_unit(self):
        qs = clarifying_questions(build_frame_spec(_complete(number_of_bays=None)))
        assert qs[0].unit is None

    def test_questions_follow_canonical_order(self):
        """Missing questions are emitted in the canonical required-field order."""
        result = build_frame_spec(FrameSpecExtraction())
        order = [q.field for q in clarifying_questions(result)]
        assert order == [
            "geometry.span_m",
            "geometry.eaves_height_m",
            "geometry.roof_pitch_deg",
            "geometry.bay_spacing_m",
            "geometry.number_of_bays",
            "dead.roof_kpa",
            "wind.basic_wind_speed_ms",
            "wind.terrain_category",
        ]


# ---------------------------------------------------------------------------
# 3. Invalid stated values -> a correction question (never silently clamp)
# ---------------------------------------------------------------------------


class TestQuestionsForInvalid:
    def test_invalid_pitch_yields_invalid_question(self):
        result = build_frame_spec(_complete(roof_pitch_deg=60.0))
        qs = clarifying_questions(result)
        assert qs, "expected a correction question for the invalid pitch"
        assert any(q.kind == "invalid" for q in qs)
        assert any("roof_pitch_deg" in q.field for q in qs)

    def test_invalid_question_mentions_the_problem(self):
        qs = clarifying_questions(build_frame_spec(_complete(span_m=-3.0)))
        assert any("not valid" in q.question.lower() for q in qs)

    def test_invalid_does_not_produce_spec(self):
        result = build_frame_spec(_complete(number_of_bays=0))
        assert result.spec is None
        assert clarifying_questions(result)


# ---------------------------------------------------------------------------
# 4. The "ask, don't guess" contract (FR-2)
# ---------------------------------------------------------------------------


class TestAskNeverGuess:
    def test_missing_means_no_spec_but_questions(self):
        result = build_frame_spec(_complete(terrain_category=None))
        assert result.spec is None          # nothing fabricated
        assert clarifying_questions(result)  # a question is returned instead

    def test_terrain_not_silently_defaulted(self):
        """Terrain must be ASKED (with options), never guessed to a category."""
        result = build_frame_spec(_complete(terrain_category=None))
        terrain_qs = [q for q in clarifying_questions(result) if q.field == "wind.terrain_category"]
        assert len(terrain_qs) == 1
        assert terrain_qs[0].options == ["A", "B", "C", "D"]


# ---------------------------------------------------------------------------
# 5. clarification_prompt — formatted user-facing message
# ---------------------------------------------------------------------------


class TestClarificationPrompt:
    def test_prompt_lists_all_questions(self):
        result = build_frame_spec(FrameSpecExtraction())
        prompt = clarification_prompt(result)
        assert prompt is not None
        # 8 numbered lines + a heading
        assert prompt.count("\n") == 8
        assert "1." in prompt and "8." in prompt

    def test_prompt_includes_terrain_options(self):
        prompt = clarification_prompt(build_frame_spec(_complete(terrain_category=None)))
        assert prompt is not None
        assert "A, B, C, D" in prompt

    def test_prompt_includes_units(self):
        prompt = clarification_prompt(build_frame_spec(_complete(span_m=None)))
        assert prompt is not None
        assert "[m]" in prompt


# ---------------------------------------------------------------------------
# 6. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_result_same_questions(self):
        r1 = build_frame_spec(FrameSpecExtraction())
        r2 = build_frame_spec(FrameSpecExtraction())
        assert clarifying_questions(r1) == clarifying_questions(r2)

    def test_questions_are_frozen(self):
        q = clarifying_questions(build_frame_spec(_complete(span_m=None)))[0]
        assert isinstance(q, ClarifyingQuestion)
        import dataclasses

        assert dataclasses.is_dataclass(q)
