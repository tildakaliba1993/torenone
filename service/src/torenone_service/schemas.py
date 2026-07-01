"""HTTP request/response schemas for the engineering service (Task 4.3+)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from torenone_ai import AgentConstraints, ParseResult, clarifying_questions
from torenone_kernel.models.frame_spec import FrameGeometry, FrameSpec
from torenone_kernel.models.results import DesignResult, SectionChoice
from torenone_kernel.report.metadata import ReportMetadata

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


class ParseDrawingRequest(BaseModel):
    """A drawing/sketch/plan of a steel portal frame (the drawings-in front door)."""

    image_data_url: str = Field(
        min_length=1,
        max_length=16_000_000,  # ~12 MB image/PDF base64-encoded (~1.37× expansion)
        description=(
            "The drawing as a data: URL (data:image/<type>;base64,... or "
            "data:application/pdf;base64,...) or an https URL."
        ),
    )
    note: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional accompanying context not shown on the drawing.",
    )

    @field_validator("image_data_url")
    @classmethod
    def _must_be_image_or_pdf(cls, value: str) -> str:
        v = value.strip()
        accepted = ("data:image/", "data:application/pdf", "https://")
        if not v.startswith(accepted):
            raise ValueError(
                "image_data_url must be a data:image/* URL, a data:application/pdf URL, or an https URL"
            )
        return v


class ProposeFrameRequest(ParseDrawingRequest):
    """An architect's general-arrangement drawing to PROPOSE a portal frame from.

    Same payload shape and validation as :class:`ParseDrawingRequest` (image/PDF/https), but the
    intent differs: the drawing is the *building*, not the frame, and the agent proposes the frame
    geometry that suits it (see torenone_ai.propose_frame_from_drawing).
    """


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
    # The FrameSpecExtraction field this answer fills — the key the clarify loop sends to /build-spec.
    input_field: str | None = None


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
    # The values the model already read (keyed by FrameSpecExtraction field), so the clarify
    # loop pre-fills what's understood and the engineer only completes the gaps. Empty when nothing
    # was parsed or the request was out of scope.
    partial: dict[str, bool | float | str | None] = {}

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
                input_field=q.input_field,
            )
            for q in clarifying_questions(result)
        ]
        assumptions = [
            ParseAssumption(field=a.field, value=_json_value(a.value), note=a.note)
            for a in result.assumptions
        ]
        # Surface the values already read (non-null extraction fields) so the clarify loop can
        # pre-fill them; never on an out-of-scope refusal.
        partial: dict[str, bool | float | str | None] = {}
        if result.extraction is not None and not result.out_of_scope:
            partial = {
                field: _json_value(value)
                for field, value in result.extraction.model_dump().items()
                if value is not None and field not in ("in_scope", "out_of_scope_reason")
            }
        return cls(
            status=status,
            spec=result.spec,
            assumptions=assumptions,
            questions=questions,
            missing=[m.field for m in result.missing],
            errors=list(result.errors),
            scope_note=result.scope_note,
            partial=partial,
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
    report_metadata: ReportMetadata | None = Field(
        default=None,
        description="Optional document/admin metadata (project, client, engineer, revision) "
        "rendered on the calc-package cover. Not engineering data.",
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


# ---------------------------------------------------------------------------
# /stamp  (registered-engineer e-stamp on a stored run)
# ---------------------------------------------------------------------------


class StampRequest(BaseModel):
    """Apply the calling registered engineer's e-stamp to a stored design run."""

    run_id: str = Field(min_length=1)


class StampResponse(BaseModel):
    """The applied stamp (the run's PDF has been re-rendered + re-stored with it)."""

    engineer_name: str
    ecsa_reg_no: str
    stamped_at: str
    fingerprint: str


# ---------------------------------------------------------------------------
# /design-agent  (agentic exploration — no PDF; the web replays the pick via /design)
# ---------------------------------------------------------------------------


class AgentDesignRequest(BaseModel):
    """A confirmed FrameSpec to explore agentically, plus optional engineer constraints."""

    spec: FrameSpec
    constraints: AgentConstraints | None = Field(
        default=None,
        description="Optional limits (stock sections, max member depth) the search must honour.",
    )
    cost_rate_zar_per_kg: float | None = Field(
        default=None, gt=0, description="Override the default fabricated-steel cost rate."
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
