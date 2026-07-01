"""Architect-GA "propose the frame" (vision) tests — the topology-slice front door.

Proves the propose-frame front door reuses the SAME safety pipeline as text/drawing parsing: the LLM
only fills the nullable FrameSpecExtraction (it proposes GEOMETRY, never an engineering number), then
the deterministic build_frame_spec flags missing fields / applies documented defaults / validates.
The vision client is injected, so these run with a fake client (no network / key).

Run:
    PYTHONPATH="kernel/src:tools:service/src" .venv/bin/pytest service/tests/test_propose_frame.py -q
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from torenone_ai.parsing import (
    PROPOSE_FROM_GA_SYSTEM_PROMPT,
    FrameSpecExtraction,
    propose_frame_from_drawing,
)
from torenone_kernel.models.enums import TerrainCategory


def _complete_extraction(**overrides: Any) -> FrameSpecExtraction:
    base: dict[str, Any] = dict(
        span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=5.0,
        number_of_bays=8, roof_dead_load_kpa=0.15, basic_wind_speed_ms=40.0,
        terrain_category=TerrainCategory.C,
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


def _client(parsed: Any, capture: dict[str, Any] | None = None) -> Any:
    return SimpleNamespace(responses=_FakeResponses(parsed, capture if capture is not None else {}))


_IMG = "data:image/png;base64,iVBORw0KGgo="  # a stand-in image data URL


def test_proposed_geometry_builds_a_valid_spec() -> None:
    # The GA gave enough to propose a complete frame (loads/wind noted on the drawing here).
    result = propose_frame_from_drawing(_IMG, client=_client(_complete_extraction()), model="gpt-5.5")
    assert result.is_complete
    assert result.spec is not None
    assert result.spec.geometry.span_m == 20.0
    assert result.spec.geometry.number_of_bays == 8


def test_sends_image_and_ga_prompt_with_structured_format() -> None:
    capture: dict[str, Any] = {}
    propose_frame_from_drawing(
        _IMG, client=_client(_complete_extraction(), capture), model="gpt-5.5", note="warehouse GA"
    )
    # Same Structured-Outputs target as every other front door — but the GA system prompt.
    assert capture["text_format"] is FrameSpecExtraction
    msgs = capture["input"]
    assert msgs[0]["role"] == "system" and msgs[0]["content"] == PROPOSE_FROM_GA_SYSTEM_PROMPT
    user_content = msgs[1]["content"]
    kinds = {block["type"] for block in user_content}
    assert kinds == {"input_text", "input_image"}
    image_block = next(b for b in user_content if b["type"] == "input_image")
    assert image_block["image_url"] == _IMG
    note_block = next(b for b in user_content if b["type"] == "input_text")
    assert note_block["text"] == "warehouse GA"


def test_loads_and_wind_absent_from_ga_are_flagged_never_guessed() -> None:
    # A realistic GA: geometry proposable, but loads + wind are not on an architectural drawing.
    proposed = FrameSpecExtraction(
        span_m=24.0, eaves_height_m=7.0, roof_pitch_deg=5.0, bay_spacing_m=6.0, number_of_bays=5
    )
    result = propose_frame_from_drawing(_IMG, client=_client(proposed), model="gpt-5.5")
    assert result.needs_clarification
    assert result.spec is None
    missing_fields = {m.field for m in result.missing}
    # Geometry proposed → not missing; loads + wind not on the GA → flagged (asked, not invented).
    assert "geometry.span_m" not in missing_fields
    assert "dead.roof_kpa" in missing_fields
    assert "wind.basic_wind_speed_ms" in missing_fields
    assert "wind.terrain_category" in missing_fields


def test_unframeable_building_is_refused() -> None:
    extraction = FrameSpecExtraction(
        in_scope=False, out_of_scope_reason="multi-storey office building"
    )
    result = propose_frame_from_drawing(_IMG, client=_client(extraction), model="gpt-5.5")
    assert result.out_of_scope
    assert result.spec is None
    assert "multi-storey" in (result.scope_note or "")


def test_unreadable_ga_flags_everything() -> None:
    result = propose_frame_from_drawing(_IMG, client=_client(None), model="gpt-5.5")
    assert not result.is_complete
    assert result.spec is None
    assert result.missing  # nothing fabricated
