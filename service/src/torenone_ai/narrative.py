"""Task 3.4 — report narrative generation.

The narrative is human-readable prose for the report. The hard rule (PRD FR-2/NFR-2):
**every engineering number comes from the kernel — never from the language model.**

How that is guaranteed (architectural, not "please be careful")
---------------------------------------------------------------
1. :func:`build_narrative_facts` derives a fixed registry of named facts from the
   :class:`~torenone_kernel.models.results.DesignResult` — this is the ONLY source
   of numbers (and number-bearing strings like section designations / clauses).
2. The language model is asked to write prose containing only ``{slot}`` placeholders
   drawn from that registry, and **no digits of its own**.
3. :func:`assert_prose_has_no_literal_numbers` rejects any model output containing a
   digit — so the model literally cannot emit a number down this path.
4. :func:`render_narrative` substitutes each ``{slot}`` with its kernel value (and
   rejects any unknown slot the model might invent).

Result: the model contributes connective prose only; all numbers in the final text
are kernel-computed values placed by deterministic substitution. A purely
deterministic narrative (:func:`deterministic_narrative`) is also provided — both a
safe fallback and a demonstration that the narrative needs no model-authored numbers.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any

from torenone_kernel.models.results import CheckResult, DesignResult

# A slot reference in prose: {slot_name}. Slot names are lower snake_case (no digits),
# so compliant model prose contains no digits at all.
_SLOT_RE = re.compile(r"\{([a-z][a-z_]*)\}")
_DIGIT_RE = re.compile(r"\d")


class NarrativeError(ValueError):
    """Base error for narrative generation."""


class NarrativeGuardError(NarrativeError):
    """Raised when model output violates the no-model-numbers guarantee."""


# ---------------------------------------------------------------------------
# 1. Facts — the ONLY source of numbers (all kernel-derived)
# ---------------------------------------------------------------------------


def _governing_check(result: DesignResult) -> CheckResult | None:
    if not result.checks:
        return None
    return max(result.checks, key=lambda c: c.utilisation)


def build_narrative_facts(result: DesignResult) -> dict[str, str]:
    """Return the named facts a narrative may reference. All values are kernel-derived.

    Every numeric value in a rendered narrative comes from this dict — never from the
    language model.
    """
    g = result.frame_spec.geometry
    w = result.frame_spec.wind
    materials = result.frame_spec.materials

    sections = {s.member: s.designation for s in result.sections}
    gov = _governing_check(result)

    facts: dict[str, str] = {
        # Geometry (transcribed inputs + pure computed geometry)
        "span_m": f"{g.span_m:g}",
        "eaves_height_m": f"{g.eaves_height_m:g}",
        "apex_height_m": f"{g.apex_height_m:.2f}",
        "roof_pitch_deg": f"{g.roof_pitch_deg:g}",
        "bay_spacing_m": f"{g.bay_spacing_m:g}",
        "number_of_bays": f"{g.number_of_bays:d}",
        "building_length_m": f"{g.building_length_m:g}",
        # Site / wind
        "basic_wind_speed_ms": f"{w.basic_wind_speed_ms:g}",
        "terrain_category": w.terrain_category.value,
        # Material
        "steel_grade": materials.steel_grade.value,
        # Chosen sections (kernel auto-sizing / check mode)
        "rafter_designation": sections.get("rafter", "n/a"),
        "column_designation": sections.get("column", "n/a"),
        # Outcome
        "status": "PASS" if result.passed else "FAIL",
        "governing_utilisation": f"{result.governing_utilisation:.2f}",
        "check_count": f"{len(result.checks):d}",
    }

    if gov is not None:
        facts["governing_check"] = gov.name
        facts["governing_clause"] = gov.clause

    if result.total_steel_mass_kg is not None:
        facts["total_steel_mass_kg"] = f"{result.total_steel_mass_kg:.0f}"
    if result.indicative_cost_zar is not None:
        facts["indicative_cost_zar"] = f"{result.indicative_cost_zar:,.0f}"

    return facts


# ---------------------------------------------------------------------------
# 2. Guard — the model may not emit any number
# ---------------------------------------------------------------------------


def assert_prose_has_no_literal_numbers(prose: str) -> None:
    """Raise NarrativeGuardError if *prose* contains any digit.

    Compliant model prose references quantities only via ``{slot}`` placeholders
    (whose names contain no digits), so any digit means the model tried to author a
    number itself — which is forbidden.
    """
    match = _DIGIT_RE.search(prose)
    if match:
        raise NarrativeGuardError(
            "Model narrative contained a literal number "
            f"(found {match.group()!r} at index {match.start()}). "
            "All numbers must come from the kernel via placeholders, never the model."
        )


# ---------------------------------------------------------------------------
# 3. Render — substitute kernel facts into slotted prose
# ---------------------------------------------------------------------------


def render_narrative(prose: str, facts: dict[str, str]) -> str:
    """Replace every ``{slot}`` in *prose* with its kernel fact value.

    Raises NarrativeError if *prose* references a slot not present in *facts*
    (so the model cannot invent an unknown fact).
    """
    unknown: list[str] = []

    def _replace(m: re.Match[str]) -> str:
        name = m.group(1)
        if name not in facts:
            unknown.append(name)
            return m.group(0)
        return facts[name]

    rendered = _SLOT_RE.sub(_replace, prose)
    if unknown:
        raise NarrativeError(
            f"Narrative referenced unknown fact(s): {sorted(set(unknown))}. "
            f"Allowed facts: {sorted(facts)}."
        )
    return rendered


# ---------------------------------------------------------------------------
# 4. Deterministic narrative (no LLM) — safe fallback + reference
# ---------------------------------------------------------------------------

_DETERMINISTIC_TEMPLATE = (
    "This single-bay steel portal frame spans {span_m} m between eaves at "
    "{eaves_height_m} m, rising to an apex at {apex_height_m} m on a {roof_pitch_deg}-degree "
    "pitch. Frames are spaced at {bay_spacing_m} m over {number_of_bays} bays "
    "({building_length_m} m overall), in {steel_grade} steel. The site wind speed is "
    "{basic_wind_speed_ms} m/s in terrain category {terrain_category}.\n\n"
    "The design result is {status}. Across {check_count} code checks the governing "
    "utilisation is {governing_utilisation}, set by the {governing_check} check "
    "({governing_clause}). The kernel selected {rafter_designation} rafters and "
    "{column_designation} columns, for an indicative frame steel mass of "
    "{total_steel_mass_kg} kg.\n\n"
    "All numbers above are computed by the deterministic TorenOne kernel and must be "
    "verified by a registered engineer before use."
)


def deterministic_narrative(result: DesignResult) -> str:
    """Build a narrative purely from kernel facts (no language model involved)."""
    return render_narrative(_DETERMINISTIC_TEMPLATE, build_narrative_facts(result))


# ---------------------------------------------------------------------------
# 5. LLM narrative — model writes slotted prose, kernel fills the numbers
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class NarrativeResult:
    """The outcome of narrative generation."""

    text: str                 # final narrative (kernel numbers substituted in)
    model_prose: str          # raw model output (slots only, no digits)
    facts: dict[str, str]     # kernel facts used for substitution


def _system_prompt(allowed_slots: list[str]) -> str:
    slot_list = ", ".join(f"{{{s}}}" for s in allowed_slots)
    return (
        "You write a short, professional summary paragraph for a structural steel "
        "portal-frame design report.\n\n"
        "ABSOLUTE RULES:\n"
        "1. You must NOT write any number, in digits or words. Not one digit.\n"
        "2. Refer to every quantity ONLY by inserting one of these exact placeholders, "
        "which the system will replace with kernel-computed values:\n"
        f"   {slot_list}\n"
        "3. Use only placeholders from that list. Do not invent new placeholders.\n"
        "4. Write 2-4 sentences of clear, factual prose. Do not editorialise or claim "
        "the design is safe — a registered engineer must verify it.\n"
        "If you are tempted to write a number, use the matching placeholder instead."
    )


def generate_narrative(result: DesignResult, *, client: Any, model: str) -> NarrativeResult:
    """Generate a report narrative whose numbers all come from the kernel.

    The model writes slotted prose (no digits); we guard that output, then substitute
    kernel facts. If the model violates the no-numbers rule, NarrativeGuardError is
    raised (the caller may fall back to :func:`deterministic_narrative`).
    """
    facts = build_narrative_facts(result)
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": _system_prompt(sorted(facts))},
            {
                "role": "user",
                "content": (
                    "Write the summary using the placeholders. Cover the geometry, the "
                    "pass/fail status, the governing check, and the chosen sections."
                ),
            },
        ],
    )
    model_prose = (getattr(response, "output_text", None) or "").strip()
    if not model_prose:
        raise NarrativeError("The model returned no narrative text.")

    # ARCHITECTURAL GUARD: the model must not have authored any number.
    assert_prose_has_no_literal_numbers(model_prose)

    text = render_narrative(model_prose, facts)
    return NarrativeResult(text=text, model_prose=model_prose, facts=facts)
