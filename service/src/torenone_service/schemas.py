"""HTTP request/response schemas for the engineering service (Task 4.3+)."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from torenone_ai import ParseResult, clarifying_questions
from torenone_kernel.models.frame_spec import FrameSpec

# ---------------------------------------------------------------------------
# /parse
# ---------------------------------------------------------------------------


class ParseRequest(BaseModel):
    """Free-text description of a steel portal frame."""

    description: str = Field(
        min_length=1,
        max_length=5000,
        description="Natural-language description of the portal frame to design.",
    )


class ParseAssumption(BaseModel):
    """A documented default applied because the user did not state the value."""

    field: str
    value: bool | float | str | None
    note: str


class ParseQuestion(BaseModel):
    """A clarifying question to put to the user (missing or invalid input)."""

    field: str
    question: str
    kind: Literal["missing", "invalid"]
    unit: str | None = None
    options: list[str] | None = None


ParseStatus = Literal["complete", "needs_clarification", "invalid", "out_of_scope"]


class ParseResponse(BaseModel):
    """Outcome of parsing a description.

    ``status`` selects which fields are meaningful:
      * ``complete``            -> ``spec`` (+ ``assumptions``)
      * ``needs_clarification`` -> ``questions`` (+ ``missing``)
      * ``invalid``             -> ``errors`` (+ ``questions``)
      * ``out_of_scope``        -> ``scope_note``
    """

    status: ParseStatus
    spec: FrameSpec | None = None
    assumptions: list[ParseAssumption] = []
    questions: list[ParseQuestion] = []
    missing: list[str] = []
    errors: list[str] = []
    scope_note: str | None = None

    @classmethod
    def from_result(cls, result: ParseResult) -> ParseResponse:
        if result.out_of_scope:
            status: ParseStatus = "out_of_scope"
        elif result.is_complete:
            status = "complete"
        elif result.missing:
            status = "needs_clarification"
        else:
            status = "invalid"

        questions = [
            ParseQuestion(
                field=q.field,
                question=q.question,
                kind="invalid" if q.kind == "invalid" else "missing",
                unit=q.unit,
                options=q.options,
            )
            for q in clarifying_questions(result)
        ]
        assumptions = [
            ParseAssumption(field=a.field, value=_json_value(a.value), note=a.note)
            for a in result.assumptions
        ]
        return cls(
            status=status,
            spec=result.spec,
            assumptions=assumptions,
            questions=questions,
            missing=[m.field for m in result.missing],
            errors=list(result.errors),
            scope_note=result.scope_note,
        )


def _json_value(value: object) -> bool | float | str | None:
    """Normalise an assumption value to a JSON-friendly scalar."""
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, bool | float | str) or value is None:
        return value
    return str(value)
