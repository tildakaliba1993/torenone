"""Task 3.3 — clarifying questions.

When a description is incomplete or contradictory, TorenOne asks a question — it
never guesses (PRD FR-2). This module turns a :class:`~torenone_ai.parsing.ParseResult`
into concrete, engineer-facing questions.

Why deterministic (no LLM)?
---------------------------
The questions are generated directly from the typed missing-field / validation
metadata, not by a language model. That guarantees we ask about *exactly* the
fields that are missing or invalid, with the correct units and the valid options
for enumerated fields — and it is fully reproducible and testable. A language
model is never asked to invent which questions to pose (that would risk guessing).
"""

from __future__ import annotations

import dataclasses

from torenone_ai.parsing import ParseResult

# ---------------------------------------------------------------------------
# Canonical question metadata, keyed by FrameSpec path.
# (question text, unit or None, enum options or None)
# ---------------------------------------------------------------------------

_FIELD_QUESTIONS: dict[str, tuple[str, str | None, list[str] | None]] = {
    "geometry.span_m": (
        "What is the clear span of the frame, measured eaves to eaves?", "m", None,
    ),
    "geometry.eaves_height_m": (
        "What is the eaves height (column height to the eaves)?", "m", None,
    ),
    "geometry.roof_pitch_deg": (
        "What is the roof pitch? (0-45 degrees)", "deg", None,
    ),
    "geometry.bay_spacing_m": (
        "What is the bay spacing (centre-to-centre distance between frames)?", "m", None,
    ),
    "geometry.number_of_bays": (
        "How many bays are there along the building length?", None, None,
    ),
    "dead.roof_kpa": (
        "What is the permanent (dead) roof load — sheeting, purlins and insulation?",
        "kPa", None,
    ),
    "wind.basic_wind_speed_ms": (
        "What is the basic wind speed (vb) for the site, from the SANS 10160-3 map?",
        "m/s", None,
    ),
    "wind.terrain_category": (
        "Which SANS 10160-3 terrain category best describes the site surroundings?",
        None, ["A", "B", "C", "D"],
    ),
    # Optional enums — included for reuse (they normally default, so rarely asked).
    "materials.steel_grade": (
        "Which steel grade should be used?", None, ["S275JR", "S355JR"],
    ),
    "base_fixity": (
        "Are the column bases pinned or fixed?", None, ["pinned", "fixed"],
    ),
}

# Secondary index by leaf field name (pydantic validation errors report the inner
# field, e.g. "roof_pitch_deg", not the full "geometry.roof_pitch_deg" path).
_LEAF_INDEX: dict[str, tuple[str, str | None, list[str] | None]] = {
    path.split(".")[-1]: meta for path, meta in _FIELD_QUESTIONS.items()
}

# Canonical FrameSpec path -> the matching FrameSpecExtraction input field. The clarify loop
# collects answers keyed by this input field and merges them deterministically (build_frame_spec),
# so the engineer's answers + whatever was already read combine WITHOUT a second LLM pass. Note
# the names are not always the leaf (dead.roof_kpa -> roof_dead_load_kpa).
_CANONICAL_TO_INPUT: dict[str, str] = {
    "geometry.span_m": "span_m",
    "geometry.eaves_height_m": "eaves_height_m",
    "geometry.roof_pitch_deg": "roof_pitch_deg",
    "geometry.bay_spacing_m": "bay_spacing_m",
    "geometry.number_of_bays": "number_of_bays",
    "dead.roof_kpa": "roof_dead_load_kpa",
    "dead.services_kpa": "services_kpa",
    "dead.wall_cladding_kpa": "wall_cladding_kpa",
    "wind.basic_wind_speed_ms": "basic_wind_speed_ms",
    "wind.terrain_category": "terrain_category",
    "wind.site_altitude_m": "site_altitude_m",
    "materials.steel_grade": "steel_grade",
    "base_fixity": "base_fixity",
}
_LEAF_TO_INPUT: dict[str, str] = {path.split(".")[-1]: inp for path, inp in _CANONICAL_TO_INPUT.items()}


def _lookup(field: str) -> tuple[str, str | None, list[str] | None] | None:
    """Resolve question metadata by full path, then by leaf field name."""
    if field in _FIELD_QUESTIONS:
        return _FIELD_QUESTIONS[field]
    return _LEAF_INDEX.get(field.split(".")[-1])


def _input_field(field: str) -> str | None:
    """The FrameSpecExtraction input name for a canonical path / validation field."""
    return _CANONICAL_TO_INPUT.get(field) or _LEAF_TO_INPUT.get(field.split(".")[-1])


@dataclasses.dataclass(frozen=True)
class ClarifyingQuestion:
    """A single question to put to the user instead of guessing a value."""

    field: str            # canonical FrameSpec path (or the field reported by validation)
    question: str         # human-readable question
    kind: str             # "missing" | "invalid"
    unit: str | None = None
    options: list[str] | None = None
    input_field: str | None = None  # the FrameSpecExtraction field the answer fills


def clarifying_questions(result: ParseResult) -> list[ClarifyingQuestion]:
    """Return the questions needed to complete/correct *result*.

    Empty when the result is already complete. One question per missing required
    field (in the canonical order) followed by one per validation error.

    An out-of-scope request is refused, not clarified, so no questions are returned.
    """
    if result.out_of_scope:
        return []

    questions: list[ClarifyingQuestion] = []

    # Missing required inputs — ask, never assume.
    for m in result.missing:
        meta = _lookup(m.field)
        if meta is not None:
            text, unit, options = meta
        else:  # robustness fallback — should not happen for known fields
            text, unit, options = f"Please provide {m.label}.", None, None
        questions.append(
            ClarifyingQuestion(
                field=m.field, question=text, kind="missing", unit=unit, options=options,
                input_field=_input_field(m.field),
            )
        )

    # Stated-but-invalid values — ask for a correction, never silently clamp.
    for err in result.errors:
        field = err.split(":", 1)[0].strip()
        meta = _lookup(field)
        unit = meta[1] if meta else None
        options = meta[2] if meta else None
        questions.append(
            ClarifyingQuestion(
                field=field,
                question=(
                    f"The value provided for '{field}' is not valid ({err}). "
                    "Please provide a corrected value."
                ),
                kind="invalid",
                unit=unit,
                options=options,
                input_field=_input_field(field),
            )
        )

    return questions


def clarification_prompt(result: ParseResult) -> str | None:
    """Format the questions as a single user-facing message, or None if complete."""
    questions = clarifying_questions(result)
    if not questions:
        return None

    lines = ["To run the design I need a few more details:"]
    for i, q in enumerate(questions, start=1):
        unit = f" [{q.unit}]" if q.unit else ""
        options = f" (options: {', '.join(q.options)})" if q.options else ""
        lines.append(f"{i}. {q.question}{unit}{options}")
    return "\n".join(lines)
