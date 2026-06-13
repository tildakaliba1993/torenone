"""Task 3.2 — OpenAI Structured-Outputs spec parsing.

Turn a free-text description into a typed kernel ``FrameSpec`` — WITHOUT the LLM
guessing any value (PRD FR-2).

How "never silently guess" is enforced
--------------------------------------
1. The LLM fills :class:`FrameSpecExtraction`, where **every field is nullable**.
   The system prompt instructs it to use ``null`` for anything not explicitly
   stated — it must not infer, compute, or invent dimensions/loads.
2. A deterministic builder, :func:`build_frame_spec`, then:
     * flags every missing **required** field (span, eaves height, pitch, bay
       spacing, number of bays, roof dead load, wind speed, terrain) — these are
       never assumed;
     * applies **documented defaults** for optional fields and records each as an
       explicit :class:`Assumption` (so the confirm screen / report can show it);
     * constructs and validates the real ``FrameSpec`` (range checks included).
3. The LLM never produces an engineering number — it only transcribes/classifies
   values the user stated; the engineer confirms everything downstream (FR-4).

The OpenAI client is injected into :func:`parse_description`, so the deterministic
mapping is fully unit-testable without any network call or API key.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from torenone_kernel.models.enums import BaseFixity, SteelGrade, TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FoundationInputs,
    FrameGeometry,
    FrameSpec,
    ImposedLoadInputs,
    Materials,
    Restraints,
    WindContext,
)

from torenone_ai.config import AIConfig

# ---------------------------------------------------------------------------
# Structured-output target — every field nullable (null = "not stated")
# ---------------------------------------------------------------------------


class FrameSpecExtraction(BaseModel):
    """All user-supplyable ``FrameSpec`` inputs, each nullable.

    This is the OpenAI Structured-Outputs schema.  The model MUST set a field to
    ``null`` when the description does not explicitly state it — it must never
    guess, infer, or compute a value.
    """

    # --- Geometry (required in FrameSpec) ---
    span_m: float | None = Field(
        None, description="Clear span, eaves to eaves, in metres. Null if not stated."
    )
    eaves_height_m: float | None = Field(
        None, description="Column height to the eaves, in metres. Null if not stated."
    )
    roof_pitch_deg: float | None = Field(
        None, description="Roof pitch in degrees (0-45). Null if not stated."
    )
    bay_spacing_m: float | None = Field(
        None,
        description="Spacing between adjacent frames (bay spacing / tributary width), "
        "in metres. Null if not stated.",
    )
    number_of_bays: int | None = Field(
        None, description="Number of bays along the building length. Null if not stated."
    )

    # --- Dead load ---
    roof_dead_load_kpa: float | None = Field(
        None,
        description="Permanent roof load (sheeting, purlins, insulation) in kPa. "
        "Null if not stated.",
    )
    services_kpa: float | None = Field(
        None, description="Additional services / M&E permanent load in kPa. Null if not stated."
    )
    wall_cladding_kpa: float | None = Field(
        None, description="Wall cladding permanent load in kPa. Null if not stated."
    )

    # --- Imposed ---
    roof_access: bool | None = Field(
        None,
        description="True only if the description says the roof is accessible (beyond "
        "normal maintenance access). Null if not stated.",
    )

    # --- Wind ---
    basic_wind_speed_ms: float | None = Field(
        None,
        description="Basic/fundamental wind speed vb in m/s (from the SANS 10160-3 map). "
        "Null if not stated.",
    )
    terrain_category: TerrainCategory | None = Field(
        None,
        description="SANS 10160-3 terrain category A, B, C or D — only if the surroundings "
        "are clearly described. Null if unclear or not stated.",
    )
    site_altitude_m: float | None = Field(
        None, description="Site altitude above sea level in metres. Null if not stated."
    )
    has_dominant_opening: bool | None = Field(
        None,
        description="True only if a large dominant opening (e.g. roller/industrial door) "
        "is described. Null if not stated.",
    )

    # --- Materials / fixity / restraints ---
    steel_grade: SteelGrade | None = Field(
        None, description="Steel grade if stated (S275JR or S355JR). Null if not stated."
    )
    base_fixity: BaseFixity | None = Field(
        None, description="Column base fixity if stated (pinned or fixed). Null if not stated."
    )
    rafter_restraint_spacing_m: float | None = Field(
        None,
        description="Purlin spacing that laterally restrains the rafter, in metres. "
        "Null if not stated.",
    )
    column_restraint_spacing_m: float | None = Field(
        None,
        description="Girt spacing that laterally restrains the column, in metres. "
        "Null if not stated.",
    )

    # --- Foundation (Task 1.18) ---
    allowable_bearing_kpa: float | None = Field(
        None,
        description="Site allowable (safe) bearing pressure in kPa — a geotechnical input. "
        "Extract ONLY if the description explicitly states it. Null if not stated; it is "
        "NEVER assumed (without it the pad footing is simply not designed).",
    )
    concrete_fcu_mpa: float | None = Field(
        None,
        description="Concrete cube strength fcu in MPa for the baseplate/footing, if stated. "
        "Null if not stated.",
    )

    # --- Scope guard (Task 3.5) ---
    in_scope: bool | None = Field(
        None,
        description="False ONLY if the description is clearly NOT a single-bay symmetric "
        "steel portal frame — e.g. multi-storey, concrete/timber, a bridge, a truss, a "
        "crane gantry, a multi-bay/multi-span building, or another structure type. "
        "True or null if it appears to be (or could be) a single-bay steel portal frame.",
    )
    out_of_scope_reason: str | None = Field(
        None,
        description="If in_scope is false, a short plain-English note of what was actually "
        "requested (e.g. 'reinforced-concrete multi-storey building'). Null otherwise.",
    )


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class MissingField:
    """A required input the description did not provide (must be clarified, not guessed)."""

    field: str   # canonical FrameSpec path, e.g. "geometry.span_m"
    label: str   # human-friendly label, e.g. "clear span (m)"
    why: str     # why it is required / cannot be assumed


@dataclasses.dataclass(frozen=True)
class Assumption:
    """A documented default applied because the user did not state the value."""

    field: str       # canonical FrameSpec path
    value: Any       # the default value applied
    note: str        # human-readable justification


@dataclasses.dataclass(frozen=True)
class ParseResult:
    """Outcome of parsing a description.

    Exactly one of these holds:
      * ``out_of_scope`` is True (the request is not a single-bay steel portal frame); or
      * ``spec`` is a valid FrameSpec and ``is_complete`` is True; or
      * ``missing`` is non-empty (needs clarification — FR-2/3.3); or
      * ``errors`` is non-empty (the stated values failed validation).
    """

    spec: FrameSpec | None
    missing: list[MissingField]
    assumptions: list[Assumption]
    errors: list[str]
    out_of_scope: bool = False
    scope_note: str | None = None

    @property
    def is_complete(self) -> bool:
        return (
            self.spec is not None
            and not self.missing
            and not self.errors
            and not self.out_of_scope
        )

    @property
    def needs_clarification(self) -> bool:
        # An out-of-scope request is refused, not clarified.
        return bool(self.missing) and not self.out_of_scope


# ---------------------------------------------------------------------------
# Deterministic mapping: extraction -> FrameSpec (no LLM, fully testable)
# ---------------------------------------------------------------------------

# (extraction attribute, canonical FrameSpec path, human label)
_REQUIRED_FIELDS: list[tuple[str, str, str]] = [
    ("span_m", "geometry.span_m", "clear span (m)"),
    ("eaves_height_m", "geometry.eaves_height_m", "eaves height (m)"),
    ("roof_pitch_deg", "geometry.roof_pitch_deg", "roof pitch (deg)"),
    ("bay_spacing_m", "geometry.bay_spacing_m", "bay spacing (m)"),
    ("number_of_bays", "geometry.number_of_bays", "number of bays"),
    ("roof_dead_load_kpa", "dead.roof_kpa", "roof permanent (dead) load (kPa)"),
    ("basic_wind_speed_ms", "wind.basic_wind_speed_ms", "basic wind speed (m/s)"),
    ("terrain_category", "wind.terrain_category", "terrain category (A-D)"),
]


def _humanise_validation_error(exc: ValidationError) -> list[str]:
    """Turn a pydantic ValidationError into readable, engineer-facing messages."""
    messages: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()))
        messages.append(f"{loc}: {err.get('msg', 'invalid value')}")
    return messages


def build_frame_spec(extraction: FrameSpecExtraction) -> ParseResult:
    """Map a (nullable) extraction to a validated FrameSpec, or flag what's missing.

    No engineering computation happens here — only required-field checks, documented
    defaults, and pydantic validation.
    """
    # 0. Scope guard — refuse (don't try to parse) anything that is not a single-bay
    #    steel portal frame, rather than asking portal-frame questions about a bridge.
    if extraction.in_scope is False:
        note = (
            extraction.out_of_scope_reason
            or "The description does not appear to be a single-bay steel portal frame."
        )
        return ParseResult(
            spec=None, missing=[], assumptions=[], errors=[],
            out_of_scope=True, scope_note=note,
        )

    # 1. Required fields are NEVER assumed — flag any that are null.
    missing = [
        MissingField(field=path, label=label, why="required input; not stated and not assumable")
        for attr, path, label in _REQUIRED_FIELDS
        if getattr(extraction, attr) is None
    ]
    if missing:
        return ParseResult(spec=None, missing=missing, assumptions=[], errors=[])

    # All required fields are guaranteed present past this point (narrows Optionals).
    assert extraction.span_m is not None
    assert extraction.eaves_height_m is not None
    assert extraction.roof_pitch_deg is not None
    assert extraction.bay_spacing_m is not None
    assert extraction.number_of_bays is not None
    assert extraction.roof_dead_load_kpa is not None
    assert extraction.basic_wind_speed_ms is not None
    assert extraction.terrain_category is not None

    # 2. Optional fields: apply documented defaults, recording each assumption.
    assumptions: list[Assumption] = []

    def resolve(attr: str, path: str, default: Any, note: str) -> Any:
        value = getattr(extraction, attr)
        if value is None:
            assumptions.append(Assumption(field=path, value=default, note=note))
            return default
        return value

    services_kpa = resolve(
        "services_kpa", "dead.services_kpa", 0.0,
        "No separate services/M&E load stated; assumed 0.0 kPa.",
    )
    wall_cladding_kpa = resolve(
        "wall_cladding_kpa", "dead.wall_cladding_kpa", 0.0,
        "No wall-cladding load stated; assumed 0.0 kPa.",
    )
    roof_access = resolve(
        "roof_access", "imposed.roof_access", False,
        "Roof access not stated; assumed inaccessible (SANS 10160-2 default category).",
    )
    site_altitude_m = resolve(
        "site_altitude_m", "wind.site_altitude_m", 0.0,
        "Site altitude not stated; assumed sea level (0 m).",
    )
    has_dominant_opening = resolve(
        "has_dominant_opening", "wind.has_dominant_opening", False,
        "No dominant opening stated; assumed none.",
    )
    steel_grade = resolve(
        "steel_grade", "materials.steel_grade", SteelGrade.S355JR,
        "Steel grade not stated; assumed S355JR (default).",
    )
    base_fixity = resolve(
        "base_fixity", "base_fixity", BaseFixity.PINNED,
        "Base fixity not stated; assumed pinned (MVP-supported base).",
    )
    rafter_restraint = resolve(
        "rafter_restraint_spacing_m", "restraints.rafter_restraint_spacing_m", None,
        "No rafter lateral restraint stated; treated as unrestrained (conservative).",
    )
    column_restraint = resolve(
        "column_restraint_spacing_m", "restraints.column_restraint_spacing_m", None,
        "No column lateral restraint stated; treated as unrestrained (conservative).",
    )
    concrete_fcu_mpa = resolve(
        "concrete_fcu_mpa", "foundation.concrete_fcu_mpa", 25.0,
        "Concrete strength not stated; assumed 25 MPa (typical SA value).",
    )
    # Allowable bearing is a geotechnical input — NEVER assumed. If the user did not
    # state it, leave it None: the kernel then designs everything except the pad footing.

    # 3. Construct + validate the real FrameSpec (range checks live in the model).
    try:
        spec = FrameSpec(
            geometry=FrameGeometry(
                span_m=extraction.span_m,
                eaves_height_m=extraction.eaves_height_m,
                roof_pitch_deg=extraction.roof_pitch_deg,
                bay_spacing_m=extraction.bay_spacing_m,
                number_of_bays=extraction.number_of_bays,
            ),
            materials=Materials(steel_grade=steel_grade),
            base_fixity=base_fixity,
            restraints=Restraints(
                rafter_restraint_spacing_m=rafter_restraint,
                column_restraint_spacing_m=column_restraint,
            ),
            dead=DeadLoadInputs(
                roof_kpa=extraction.roof_dead_load_kpa,
                services_kpa=services_kpa,
                wall_cladding_kpa=wall_cladding_kpa,
            ),
            imposed=ImposedLoadInputs(roof_access=roof_access),
            wind=WindContext(
                basic_wind_speed_ms=extraction.basic_wind_speed_ms,
                terrain_category=extraction.terrain_category,
                site_altitude_m=site_altitude_m,
                has_dominant_opening=has_dominant_opening,
            ),
            foundation=FoundationInputs(
                allowable_bearing_kpa=extraction.allowable_bearing_kpa,
                concrete_fcu_mpa=concrete_fcu_mpa,
            ),
        )
    except ValidationError as exc:
        return ParseResult(
            spec=None, missing=[], assumptions=assumptions,
            errors=_humanise_validation_error(exc),
        )

    return ParseResult(spec=spec, missing=[], assumptions=assumptions, errors=[])


# ---------------------------------------------------------------------------
# OpenAI call
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a transcription assistant for a structural-engineering tool. The user "
    "describes a single-bay steel portal frame. Extract ONLY the values they explicitly "
    "state.\n\n"
    "HARD RULES:\n"
    "1. If a value is not explicitly stated, set it to null. NEVER guess, infer, or "
    "invent a value.\n"
    "2. Do NOT perform any engineering calculation. Only transcribe stated numbers and "
    "convert units.\n"
    "3. Convert all lengths to metres, loads to kPa, wind speed to m/s, and pitch to "
    "degrees.\n"
    "4. Set terrain_category only if the surroundings are clearly described; otherwise "
    "null.\n"
    "5. If you are unsure about any field, it MUST be null. A clarifying question is "
    "always better than a guess.\n"
    "6. If the same quantity is stated more than once with conflicting/contradictory "
    "values, set that field to null (do not pick one).\n"
    "7. SCOPE: this tool only designs single-bay symmetric steel portal frames. If the "
    "description is clearly a different structure (multi-storey, concrete/timber, a "
    "bridge, a truss, a crane gantry, a multi-bay/multi-span building, etc.), set "
    "in_scope=false and give a short out_of_scope_reason. Otherwise leave in_scope null."
)


def parse_description(text: str, *, client: Any, model: str) -> ParseResult:
    """Parse *text* into a :class:`ParseResult` using an OpenAI client.

    Parameters
    ----------
    text:
        The user's free-text description of the frame.
    client:
        An OpenAI client (``openai.OpenAI``) — injected for testability.
    model:
        The model id (e.g. ``"gpt-5.5"``).

    The LLM only fills the nullable :class:`FrameSpecExtraction`; all defaulting,
    missing-field flagging and validation happen deterministically afterwards.
    """
    response = client.responses.parse(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        text_format=FrameSpecExtraction,
    )
    extraction = getattr(response, "output_parsed", None)
    if extraction is None:
        # The model returned nothing usable — flag everything as needing clarification
        # rather than fabricating a spec.
        return ParseResult(
            spec=None,
            missing=[
                MissingField(field=path, label=label, why="description could not be parsed")
                for _attr, path, label in _REQUIRED_FIELDS
            ],
            assumptions=[],
            errors=["The description could not be parsed into a frame specification."],
        )
    return build_frame_spec(extraction)


def parse_description_from_env(text: str, *, config: AIConfig | None = None) -> ParseResult:
    """Convenience wrapper: build the OpenAI client from env config and parse *text*."""
    from torenone_ai.client import build_client

    cfg = config or AIConfig.from_env()
    return parse_description(text, client=build_client(cfg), model=cfg.model)
