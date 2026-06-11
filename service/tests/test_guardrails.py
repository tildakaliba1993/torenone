"""Task 3.5 — guardrail tests.

Adversarial inputs (nonsense, out-of-scope, contradictory, invalid) must be handled
gracefully (PRD FR-3, §9): never crash, never fabricate a spec — always return a
clear, typed outcome (refuse / ask / report invalid).

The OpenAI call is exercised with a fake client (no network / key).

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_guardrails.py -q
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from torenone_ai.clarify import clarification_prompt, clarifying_questions
from torenone_ai.parsing import (
    SYSTEM_PROMPT,
    FrameSpecExtraction,
    ParseResult,
    build_frame_spec,
    parse_description,
)
from torenone_kernel.models.enums import TerrainCategory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _complete(**overrides: Any) -> FrameSpecExtraction:
    base: dict[str, Any] = dict(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0, bay_spacing_m=6.0,
        number_of_bays=5, roof_dead_load_kpa=0.20, basic_wind_speed_ms=36.0,
        terrain_category=TerrainCategory.B,
    )
    base.update(overrides)
    return FrameSpecExtraction(**base)


class _FakeClient:
    def __init__(self, parsed: Any) -> None:
        self.capture: dict[str, Any] = {}
        client = self

        class _Responses:
            def parse(self, **kwargs: Any) -> Any:
                client.capture.update(kwargs)
                return SimpleNamespace(output_parsed=parsed)

        self.responses = _Responses()


def _assert_graceful(result: ParseResult) -> None:
    """A graceful outcome never fabricates a spec unless it is genuinely complete."""
    assert isinstance(result, ParseResult)
    if result.is_complete:
        assert result.spec is not None
    else:
        assert result.spec is None
        # exactly one actionable signal is raised
        assert result.out_of_scope or result.missing or result.errors


# ---------------------------------------------------------------------------
# 1. Nonsense / empty descriptions -> ask, don't crash
# ---------------------------------------------------------------------------


class TestNonsense:
    def test_empty_extraction_asks_for_details(self):
        result = build_frame_spec(FrameSpecExtraction())
        _assert_graceful(result)
        assert result.needs_clarification
        assert not result.out_of_scope

    def test_nonsense_via_parse_does_not_crash(self):
        client = _FakeClient(FrameSpecExtraction())  # model extracted nothing
        result = parse_description("asdf qwerty zzz", client=client, model="gpt-5.5")
        _assert_graceful(result)
        assert result.needs_clarification

    def test_unparseable_output_is_graceful(self):
        client = _FakeClient(None)  # model returned nothing usable
        result = parse_description("???", client=client, model="gpt-5.5")
        _assert_graceful(result)
        assert result.spec is None
        assert result.missing and result.errors


# ---------------------------------------------------------------------------
# 2. Out-of-scope -> refuse with a reason (no portal-frame questions)
# ---------------------------------------------------------------------------


class TestOutOfScope:
    def test_out_of_scope_flagged(self):
        x = FrameSpecExtraction(
            in_scope=False, out_of_scope_reason="reinforced-concrete multi-storey building"
        )
        result = build_frame_spec(x)
        _assert_graceful(result)
        assert result.out_of_scope
        assert result.scope_note == "reinforced-concrete multi-storey building"

    def test_out_of_scope_is_not_complete_or_clarification(self):
        result = build_frame_spec(FrameSpecExtraction(in_scope=False))
        assert result.is_complete is False
        assert result.needs_clarification is False

    def test_out_of_scope_default_note(self):
        result = build_frame_spec(FrameSpecExtraction(in_scope=False))
        assert result.scope_note  # a default refusal message is provided

    def test_out_of_scope_asks_no_questions(self):
        result = build_frame_spec(FrameSpecExtraction(in_scope=False))
        assert clarifying_questions(result) == []
        assert clarification_prompt(result) is None

    def test_out_of_scope_wins_even_with_dimensions(self):
        """A multi-bay shed with a stated span is still refused, not parsed."""
        x = _complete(in_scope=False, out_of_scope_reason="multi-bay building")
        result = build_frame_spec(x)
        assert result.out_of_scope
        assert result.spec is None

    def test_out_of_scope_via_parse(self):
        client = _FakeClient(
            FrameSpecExtraction(in_scope=False, out_of_scope_reason="a steel road bridge")
        )
        result = parse_description("design a steel road bridge", client=client, model="gpt-5.5")
        _assert_graceful(result)
        assert result.out_of_scope
        assert "bridge" in (result.scope_note or "")


# ---------------------------------------------------------------------------
# 3. Contradictory inputs -> field nulled -> asked (never silently picked)
# ---------------------------------------------------------------------------


class TestContradictory:
    def test_contradicted_required_field_is_asked(self):
        """The model nulls a contradictory value (per the prompt); we then ask for it."""
        result = build_frame_spec(_complete(span_m=None))  # span stated twice, conflicting
        _assert_graceful(result)
        assert any(m.field == "geometry.span_m" for m in result.missing)

    def test_prompt_instructs_null_on_contradiction(self):
        lowered = SYSTEM_PROMPT.lower()
        assert "conflicting" in lowered or "contradictory" in lowered
        assert "null" in lowered


# ---------------------------------------------------------------------------
# 4. Invalid / out-of-range stated values -> reported, not clamped
# ---------------------------------------------------------------------------


class TestInvalidValues:
    @pytest.mark.parametrize(
        "override",
        [
            {"roof_pitch_deg": 75.0},   # > 45 (out of MVP scope)
            {"span_m": -5.0},           # non-positive
            {"number_of_bays": 0},      # < 1
            {"roof_dead_load_kpa": -1.0},
        ],
    )
    def test_invalid_value_is_reported(self, override: dict[str, Any]):
        result = build_frame_spec(_complete(**override))
        _assert_graceful(result)
        assert result.errors
        assert result.spec is None

    def test_invalid_does_not_raise(self):
        # The whole point: invalid input is data, not an exception.
        build_frame_spec(_complete(roof_pitch_deg=90.0))


# ---------------------------------------------------------------------------
# 5. Valid frames still pass the scope guard
# ---------------------------------------------------------------------------


class TestScopeDoesNotBlockValid:
    def test_in_scope_none_builds_normally(self):
        result = build_frame_spec(_complete())  # in_scope defaults to None
        assert result.is_complete
        assert result.spec is not None

    def test_in_scope_true_builds_normally(self):
        result = build_frame_spec(_complete(in_scope=True))
        assert result.is_complete


# ---------------------------------------------------------------------------
# 6. Robustness — every adversarial category yields a graceful ParseResult
# ---------------------------------------------------------------------------


class TestNoUnhandledPaths:
    @pytest.mark.parametrize(
        "extraction",
        [
            FrameSpecExtraction(),                                   # nothing
            FrameSpecExtraction(in_scope=False),                     # out of scope
            FrameSpecExtraction(span_m=15.0),                        # partial
            FrameSpecExtraction(roof_pitch_deg=80.0),                # invalid + partial
        ],
    )
    def test_build_is_always_graceful(self, extraction: FrameSpecExtraction):
        _assert_graceful(build_frame_spec(extraction))
