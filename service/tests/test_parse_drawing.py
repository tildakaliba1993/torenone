"""Drawings/plans-in (vision) parsing tests — the first AI-agent capability.

Proves the vision front door reuses the SAME safety pipeline as text parsing: the LLM only fills the
nullable FrameSpecExtraction (it transcribes labelled values, never computes), then the deterministic
build_frame_spec flags missing fields / applies documented defaults / validates. The vision client is
injected, so these run with a fake client (no network / key).

Run:
    PYTHONPATH="kernel/src:tools:service/src" .venv/bin/pytest service/tests/test_parse_drawing.py -q
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from torenone_ai.parsing import (
    VISION_SYSTEM_PROMPT,
    FrameSpecExtraction,
    image_data_url,
    parse_drawing,
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


def test_complete_drawing_builds_a_valid_spec() -> None:
    result = parse_drawing(_IMG, client=_client(_complete_extraction()), model="gpt-5.5")
    assert result.is_complete
    assert result.spec is not None
    assert result.spec.geometry.span_m == 20.0
    assert result.spec.geometry.roof_pitch_deg == 10.0


def test_sends_image_and_vision_prompt_with_structured_format() -> None:
    capture: dict[str, Any] = {}
    parse_drawing(_IMG, client=_client(_complete_extraction(), capture), model="gpt-5.5", note="rural site")
    # Same Structured-Outputs target as text parsing.
    assert capture["text_format"] is FrameSpecExtraction
    msgs = capture["input"]
    assert msgs[0]["role"] == "system" and msgs[0]["content"] == VISION_SYSTEM_PROMPT
    user_content = msgs[1]["content"]
    kinds = {block["type"] for block in user_content}
    assert kinds == {"input_text", "input_image"}, "must send both the note and the image"
    image_block = next(b for b in user_content if b["type"] == "input_image")
    assert image_block["image_url"] == _IMG
    note_block = next(b for b in user_content if b["type"] == "input_text")
    assert note_block["text"] == "rural site"


def test_missing_dimensions_are_flagged_never_guessed() -> None:
    # The drawing showed span + pitch but no eaves height / bay / loads / wind → flagged.
    partial = FrameSpecExtraction(span_m=18.0, roof_pitch_deg=7.0)
    result = parse_drawing(_IMG, client=_client(partial), model="gpt-5.5")
    assert result.needs_clarification
    assert result.spec is None
    missing_fields = {m.field for m in result.missing}
    assert "geometry.eaves_height_m" in missing_fields
    assert "wind.basic_wind_speed_ms" in missing_fields


def test_out_of_scope_drawing_is_refused() -> None:
    extraction = FrameSpecExtraction(in_scope=False, out_of_scope_reason="multi-storey concrete frame")
    result = parse_drawing(_IMG, client=_client(extraction), model="gpt-5.5")
    assert result.out_of_scope
    assert result.spec is None
    assert "multi-storey" in (result.scope_note or "")


def test_unparseable_image_flags_everything() -> None:
    result = parse_drawing(_IMG, client=_client(None), model="gpt-5.5")
    assert not result.is_complete
    assert result.spec is None
    assert result.missing  # all required fields flagged, nothing fabricated


def test_image_data_url_roundtrip() -> None:
    url = image_data_url(b"\x89PNG\r\n", "image/png")
    assert url.startswith("data:image/png;base64,")
    import base64

    payload = url.split(",", 1)[1]
    assert base64.b64decode(payload) == b"\x89PNG\r\n"
