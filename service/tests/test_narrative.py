"""Task 3.4 — narrative-generation tests.

Headline guarantee (PRD FR-2 / NFR-2): **no engineering number originates from the
language-model output path.** All numbers come from the kernel; the model only
writes connective prose with placeholders.

The OpenAI call is exercised with a fake client (no network / key).

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_narrative.py -q
"""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

import pytest
from torenone_ai.narrative import (
    NarrativeError,
    NarrativeGuardError,
    assert_prose_has_no_literal_numbers,
    build_narrative_facts,
    deterministic_narrative,
    generate_narrative,
    render_narrative,
)
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def result():
    spec = FrameSpec(
        geometry=FrameGeometry(
            span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
            bay_spacing_m=6.0, number_of_bays=5,
        ),
        dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
        wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
    )
    return design(spec)


@pytest.fixture(scope="module")
def facts(result):
    return build_narrative_facts(result)


class _FakeResponses:
    def __init__(self, output_text: str, capture: dict[str, Any]) -> None:
        self._text = output_text
        self._capture = capture

    def create(self, **kwargs: Any) -> Any:
        self._capture.update(kwargs)
        return SimpleNamespace(output_text=self._text)


class _FakeClient:
    def __init__(self, output_text: str) -> None:
        self.capture: dict[str, Any] = {}
        self.responses = _FakeResponses(output_text, self.capture)


def _numbers_not_from_facts(text: str, facts: dict[str, str]) -> str:
    """Remove every kernel fact value from *text*; return whatever digits remain.

    If the empty string (no digits) remains, every number in *text* came from the
    kernel facts — i.e. none was authored by the model.
    """
    stripped = text
    for value in sorted(facts.values(), key=len, reverse=True):
        stripped = stripped.replace(value, "")
    return "".join(re.findall(r"\d+", stripped))


# ---------------------------------------------------------------------------
# 1. Facts — the single source of numbers, all kernel-derived
# ---------------------------------------------------------------------------


class TestFacts:
    def test_geometry_facts_match_kernel(self, result, facts):
        g = result.frame_spec.geometry
        assert facts["span_m"] == f"{g.span_m:g}"
        assert facts["eaves_height_m"] == f"{g.eaves_height_m:g}"
        assert facts["number_of_bays"] == str(g.number_of_bays)

    def test_utilisation_fact_matches_kernel(self, result, facts):
        assert facts["governing_utilisation"] == f"{result.governing_utilisation:.2f}"

    def test_section_facts_match_kernel(self, result, facts):
        designations = {s.member: s.designation for s in result.sections}
        assert facts["rafter_designation"] == designations["rafter"]
        assert facts["column_designation"] == designations["column"]

    def test_status_is_word_not_number(self, facts):
        assert facts["status"] in {"PASS", "FAIL"}

    def test_mass_and_cost_present(self, result, facts):
        assert facts["total_steel_mass_kg"] == f"{result.total_steel_mass_kg:.0f}"
        assert facts["indicative_cost_zar"] == f"{result.indicative_cost_zar:,.0f}"

    def test_governing_clause_is_kernel_clause(self, result, facts):
        gov = max(result.checks, key=lambda c: c.utilisation)
        assert facts["governing_clause"] == gov.clause


# ---------------------------------------------------------------------------
# 2. The guard — the model may not emit a number
# ---------------------------------------------------------------------------


class TestGuard:
    def test_clean_prose_passes(self):
        assert_prose_has_no_literal_numbers("The frame spans {span_m} m and is {status}.")

    def test_digit_in_prose_raises(self):
        with pytest.raises(NarrativeGuardError):
            assert_prose_has_no_literal_numbers("The frame spans 15 m.")

    def test_single_digit_anywhere_raises(self):
        with pytest.raises(NarrativeGuardError):
            assert_prose_has_no_literal_numbers("Utilisation is about 0.9 which is fine.")


# ---------------------------------------------------------------------------
# 3. Render — substitute kernel facts; reject invented slots
# ---------------------------------------------------------------------------


class TestRender:
    def test_substitutes_known_slots(self, facts):
        out = render_narrative("Span {span_m} m, status {status}.", facts)
        assert facts["span_m"] in out
        assert facts["status"] in out
        assert "{span_m}" not in out

    def test_unknown_slot_raises(self, facts):
        with pytest.raises(NarrativeError):
            render_narrative("Bogus {made_up_number} here.", facts)

    def test_numbers_in_render_come_from_facts(self, facts):
        out = render_narrative(
            "Span {span_m} m at {governing_utilisation} utilisation.", facts
        )
        assert _numbers_not_from_facts(out, facts) == ""


# ---------------------------------------------------------------------------
# 4. Deterministic narrative (no LLM) — proves numbers need no model
# ---------------------------------------------------------------------------


class TestDeterministicNarrative:
    def test_contains_kernel_values(self, result, facts):
        text = deterministic_narrative(result)
        assert facts["rafter_designation"] in text
        assert facts["governing_utilisation"] in text
        assert facts["span_m"] in text

    def test_every_number_traces_to_kernel(self, result, facts):
        """After removing all kernel fact values, no digit remains."""
        text = deterministic_narrative(result)
        assert _numbers_not_from_facts(text, facts) == ""

    def test_mentions_engineer_verification(self, result):
        assert "registered engineer" in deterministic_narrative(result).lower()


# ---------------------------------------------------------------------------
# 5. LLM narrative (fake client) — model writes slots, kernel fills numbers
# ---------------------------------------------------------------------------

_GOOD_PROSE = (
    "This {span_m} m portal frame in {steel_grade} steel returned a {status} result, "
    "with a governing utilisation of {governing_utilisation} on the {governing_check} "
    "check. The kernel chose {rafter_designation} rafters and {column_designation} columns."
)


class TestGenerateNarrative:
    def test_renders_model_prose_with_kernel_numbers(self, result, facts):
        client = _FakeClient(_GOOD_PROSE)
        out = generate_narrative(result, client=client, model="gpt-5.5")
        assert facts["span_m"] in out.text
        assert facts["rafter_designation"] in out.text
        assert "{span_m}" not in out.text

    def test_model_prose_has_no_numbers(self, result):
        client = _FakeClient(_GOOD_PROSE)
        out = generate_narrative(result, client=client, model="gpt-5.5")
        assert not re.search(r"\d", out.model_prose)

    def test_final_numbers_all_trace_to_kernel(self, result, facts):
        """The headline guarantee: no number in the output came from the model."""
        client = _FakeClient(_GOOD_PROSE)
        out = generate_narrative(result, client=client, model="gpt-5.5")
        assert _numbers_not_from_facts(out.text, facts) == ""

    def test_model_authored_number_is_rejected(self, result):
        """If the model writes a number itself, the guard rejects the whole narrative."""
        client = _FakeClient("The utilisation is 0.95, comfortably within capacity.")
        with pytest.raises(NarrativeGuardError):
            generate_narrative(result, client=client, model="gpt-5.5")

    def test_model_invented_slot_is_rejected(self, result):
        client = _FakeClient("The frame uses {fake_capacity} throughout.")
        with pytest.raises(NarrativeError):
            generate_narrative(result, client=client, model="gpt-5.5")

    def test_empty_model_output_raises(self, result):
        client = _FakeClient("   ")
        with pytest.raises(NarrativeError):
            generate_narrative(result, client=client, model="gpt-5.5")

    def test_system_prompt_forbids_numbers(self, result):
        client = _FakeClient(_GOOD_PROSE)
        generate_narrative(result, client=client, model="gpt-5.5")
        system_msg = next(m for m in client.capture["input"] if m["role"] == "system")
        assert "not write any number" in system_msg["content"].lower()


# ---------------------------------------------------------------------------
# 6. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_facts_are_deterministic(self, result):
        assert build_narrative_facts(result) == build_narrative_facts(result)

    def test_deterministic_narrative_is_stable(self, result):
        assert deterministic_narrative(result) == deterministic_narrative(result)
