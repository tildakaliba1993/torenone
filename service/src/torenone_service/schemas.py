"""HTTP request/response schemas for the engineering service (Task 4.3+)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from torenone_ai import ParseResult, clarifying_questions
from torenone_kernel.models.frame_spec import FrameGeometry, FrameSpec
from torenone_kernel.models.results import DesignResult, SectionChoice

# Computed (output-only) geometry fields, stripped from inbound specs so a spec
# round-tripped from /parse (which serialises them) re-validates under extra="forbid".
_GEOMETRY_COMPUTED: frozenset[str] = frozenset(FrameGeometry.model_computed_fields)

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


# ---------------------------------------------------------------------------
# /design
# ---------------------------------------------------------------------------


class DesignRequest(BaseModel):
    """A confirmed FrameSpec to design, or to check against supplied sections."""

    spec: FrameSpec
    mode: Literal["design", "check"] = "design"
    sections: list[SectionChoice] | None = Field(
        default=None,
        description="Engineer-supplied sections (required for mode=check).",
    )
    cost_rate_zar_per_kg: float | None = Field(
        default=None, gt=0, description="Override the default fabricated-steel cost rate."
    )
    project_id: str | None = Field(
        default=None, description="Project to attach the run/report to (persistence)."
    )

    @field_validator("spec", mode="before")
    @classmethod
    def _drop_computed_geometry(cls, value: Any) -> Any:
        """Strip read-only computed geometry fields so a serialised spec re-validates."""
        if isinstance(value, dict):
            geometry = value.get("geometry")
            if isinstance(geometry, dict) and any(k in geometry for k in _GEOMETRY_COMPUTED):
                cleaned = {k: v for k, v in geometry.items() if k not in _GEOMETRY_COMPUTED}
                return {**value, "geometry": cleaned}
        return value


class StoredReport(BaseModel):
    """A persisted report PDF (storage reference, not the bytes)."""

    run_id: str
    report_id: str
    storage_path: str
    content_type: str = "application/pdf"
    size_bytes: int


class DesignResponse(BaseModel):
    """The kernel result plus a reference to the stored calc-package PDF."""

    result: DesignResult
    report: StoredReport
