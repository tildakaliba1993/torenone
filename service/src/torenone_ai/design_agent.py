"""The agentic design loop — an AI that *orchestrates* the deterministic kernel.

The hard rule, identical to every other TorenOne AI surface (PRD FR-2/NFR-2,
see :mod:`torenone_ai.narrative`): **the language model never computes or states an
engineering number. The kernel does all arithmetic; an accredited engineer stamps.**

How that is guaranteed here (architectural, not "please be careful")
-------------------------------------------------------------------
1. The model's ONLY power is to choose the next **tool call** from a tiny fixed set
   (:class:`AgentAction`): ``list_sections`` (catalogue lookup), ``run_design`` /
   ``run_check`` (run the kernel), or ``stop``. It cannot emit a utilisation, a
   capacity, a mass or a pass/fail — those values only ever come *back* from the
   kernel via :class:`~torenone_kernel.models.results.DesignResult`.
2. Every number presented to the user is read straight off a kernel result. The
   model's free-text fields (``label`` / ``rationale``) are **guarded to contain no
   digit** (:func:`torenone_ai.narrative.assert_prose_has_no_literal_numbers`); a
   non-compliant value is replaced with a deterministic fallback, never shown raw.
3. Mandatory checks can never be skipped: the only kernel tools that exist
   (``design`` / ``check``) always run the *full* SANS check set. There is
   deliberately no tool to disable a check or override an advisory flag.
4. The loop is **bounded** (max actions / candidates; the route adds a wall-clock
   budget). If the model is unavailable or errors, the loop degrades cleanly to the
   plain deterministic baseline.
5. **The result can never be worse than today's plain design**: the deterministic
   ``design(spec)`` baseline is always computed and always a candidate. The "best"
   choice is decided by deterministic code reading kernel masses — never by the model.

The model contributes *search* (which input levers to try) and *qualitative colour*
(number-free rationale). Selection, costing and pass/fail are pure kernel + pure code.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
from torenone_kernel.analysis.sway_check import FrameUnstableError
from torenone_kernel.checks.autosize import NoSectionFoundError
from torenone_kernel.design import DEFAULT_COST_RATE_ZAR_PER_KG, check, design
from torenone_kernel.models.frame_spec import FrameSpec
from torenone_kernel.models.results import DesignResult, SectionChoice
from torenone_kernel.sections.library import SectionLibrary

from torenone_ai.narrative import (
    NarrativeGuardError,
    assert_prose_has_no_literal_numbers,
)

# --------------------------------------------------------------------------- #
# Bounds — physical sanity + cost guards (enforced regardless of model output)
# --------------------------------------------------------------------------- #

# A purlin/girt restraint spacing outside this range is physically implausible for a
# single-bay portal; reject rather than feed the kernel nonsense.
MIN_RESTRAINT_SPACING_M: float = 0.5
MAX_RESTRAINT_SPACING_M: float = 12.0

# Loop budget. Each action is one kernel run or one catalogue lookup; the route also
# bounds wall-clock. Kept small to bound OpenAI cost and latency.
MAX_ACTIONS: int = 14
MAX_CANDIDATES: int = 8


class AgentBudgetError(RuntimeError):
    """Internal sentinel — the action/candidate budget was exhausted."""


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


class AgentConstraints(BaseModel):
    """Real-world limits the engineer states up front; enforced by the loop.

    These are *inputs* (like a section the user has in stock, or a clearance limit) —
    never engineering results. The kernel still computes whether a constrained design
    actually passes.
    """

    model_config = ConfigDict(extra="forbid")

    allowed_sections: list[str] | None = Field(
        default=None,
        description=(
            "If set, members may ONLY use these section designations (e.g. sections the "
            "fabricator has in stock). Both rafter and column must come from this list."
        ),
    )
    max_depth_mm: float | None = Field(
        default=None,
        gt=0,
        description="If set, no member section may be deeper than this (e.g. headroom/clearance).",
    )

    def is_active(self) -> bool:
        return bool(self.allowed_sections) or self.max_depth_mm is not None


# --------------------------------------------------------------------------- #
# The model's only output: the next tool call
# --------------------------------------------------------------------------- #


class AgentAction(BaseModel):
    """The single structured choice the model may make each step: which tool to call.

    This is the *entire* action space. The model cannot do anything not expressible
    here — and nothing here lets it state an engineering number.
    """

    model_config = ConfigDict(extra="forbid")

    tool: Literal["list_sections", "run_design", "run_check", "stop"]

    # Number-free human labels (guarded). Optional — defaulted to "" so the model may
    # omit them on ``list_sections`` / ``stop``.
    label: str = ""
    rationale: str = ""

    # Levers for run_design / run_check (all are kernel *inputs*, not results).
    rafter_restraint_spacing_m: float | None = None
    column_restraint_spacing_m: float | None = None

    # Sections to verify (run_check only).
    rafter_designation: str | None = None
    column_designation: str | None = None

    # Filter for list_sections only.
    max_depth_mm: float | None = None


class Proposer(Protocol):
    """Picks the next :class:`AgentAction` given the running transcript.

    Injected so tests can drive the loop deterministically with a scripted proposer;
    in production :class:`OpenAIProposer` wraps the model.
    """

    def __call__(self, transcript: list[dict[str, Any]]) -> AgentAction: ...


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #


class AgentAlternative(BaseModel):
    """One kernel-verified design option produced during the loop.

    ``result`` is the authoritative kernel output (sections, every check + utilisation,
    mass, cost) — the source of truth. The text fields are number-free colour.
    """

    model_config = ConfigDict(extra="forbid")

    label: str
    rationale: str
    mode: Literal["design", "check"]
    rafter_restraint_spacing_m: float | None = None
    column_restraint_spacing_m: float | None = None
    sections: list[SectionChoice] | None = None
    result: DesignResult
    mass_delta_kg: float | None = Field(
        default=None,
        description="Frame steel mass vs the baseline (kg); negative = lighter. Kernel-derived.",
    )
    trade_off_note: str = Field(
        default="",
        description="Deterministic, kernel-derived note on what this option costs/saves.",
    )


class AgentDesignOutcome(BaseModel):
    """The full result of an agentic design exploration — the /design-agent response.

    No PDF is produced here: this is exploration only. The web replays the chosen
    option through the unchanged ``/design`` path to get the stamped calc package.
    """

    model_config = ConfigDict(extra="forbid")

    baseline: DesignResult | None = Field(
        default=None,
        description="The plain deterministic design (current behaviour). None if it could not close.",
    )
    baseline_note: str | None = Field(
        default=None,
        description="Why the baseline could not close (e.g. no section in the library fits).",
    )
    alternatives: list[AgentAlternative] = Field(default_factory=list)
    recommended_index: int | None = Field(
        default=None,
        description=(
            "Index into `alternatives` of the recommended option, or None to recommend the "
            "baseline. Decided by deterministic code reading kernel masses, never by the model."
        ),
    )
    narrative: str = Field(
        default="",
        description="Plain-language summary of the exploration (all numbers kernel-derived).",
    )
    notes: list[str] = Field(default_factory=list)
    used_llm: bool = Field(
        default=False,
        description="False if the loop degraded to the deterministic baseline only (no model).",
    )


# --------------------------------------------------------------------------- #
# Kernel tools — the only powers the loop (and thus the model) has
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class _Candidate:
    """A kernel-verified design produced by a tool call (internal)."""

    label: str
    rationale: str
    mode: Literal["design", "check"]
    rafter_restraint_spacing_m: float | None
    column_restraint_spacing_m: float | None
    sections: list[SectionChoice] | None
    result: DesignResult

    def key(self) -> tuple[Any, ...]:
        """Identity for de-duplication (same inputs => same kernel result)."""
        secs = tuple(sorted((s.member, s.designation) for s in (self.sections or [])))
        return (
            self.mode,
            self.rafter_restraint_spacing_m,
            self.column_restraint_spacing_m,
            secs,
        )


def _safe_prose(text: str, fallback: str) -> str:
    """Return *text* if it is number-free, else *fallback*.

    The model's free text must never carry a digit into the UI (that would be a
    model-authored number). Compliant rationale is qualitative ("brace the rafter more
    closely"); the actual lever values are echoed deterministically elsewhere.
    """
    text = (text or "").strip()
    if not text:
        return fallback
    try:
        assert_prose_has_no_literal_numbers(text)
    except NarrativeGuardError:
        return fallback
    return text


def _clamp_spacing(value: float | None) -> float | None:
    """Reject an out-of-range restraint spacing (return None => kernel default)."""
    if value is None:
        return None
    if value < MIN_RESTRAINT_SPACING_M or value > MAX_RESTRAINT_SPACING_M:
        raise ValueError(
            f"restraint spacing must be between {MIN_RESTRAINT_SPACING_M:g} and "
            f"{MAX_RESTRAINT_SPACING_M:g} m"
        )
    return value


class KernelDesignTools:
    """Thin, deterministic wrappers over the kernel — the loop's entire toolbox.

    Every method returns a compact *observation* dict whose numbers are all kernel
    outputs. Bad inputs (out-of-range spacing, unknown/constrained section, a frame
    that will not close) become an ``{"error": ...}`` observation — never an exception
    that escapes the loop.
    """

    def __init__(
        self,
        spec: FrameSpec,
        *,
        cost_rate_zar_per_kg: float,
        constraints: AgentConstraints,
        library: SectionLibrary | None = None,
    ) -> None:
        self._spec = spec
        self._rate = cost_rate_zar_per_kg
        self._constraints = constraints
        self._library = library or SectionLibrary.load_default()
        self.candidates: list[_Candidate] = []

    # -- spec assembly ----------------------------------------------------- #

    def _spec_with_restraints(
        self, rafter_m: float | None, column_m: float | None
    ) -> FrameSpec:
        """Return a copy of the base spec with restraint overrides applied (immutably)."""
        updates: dict[str, float | None] = {}
        if rafter_m is not None:
            updates["rafter_restraint_spacing_m"] = rafter_m
        if column_m is not None:
            updates["column_restraint_spacing_m"] = column_m
        if not updates:
            return self._spec
        new_restraints = self._spec.restraints.model_copy(update=updates)
        return self._spec.model_copy(update={"restraints": new_restraints})

    # -- constraint enforcement ------------------------------------------- #

    def _section_allowed(self, designation: str) -> str | None:
        """Return an error string if *designation* violates a constraint, else None."""
        if designation not in self._library:
            return f"unknown section {designation!r}"
        if self._constraints.allowed_sections is not None:
            if designation not in self._constraints.allowed_sections:
                return f"{designation!r} is not in the allowed (stock) section list"
        if self._constraints.max_depth_mm is not None:
            depth = self._library.get(designation).depth_mm
            if depth > self._constraints.max_depth_mm:
                return (
                    f"{designation!r} is {depth:g} mm deep, over the "
                    f"{self._constraints.max_depth_mm:g} mm limit"
                )
        return None

    # -- tools ------------------------------------------------------------- #

    def list_sections(self, *, max_depth_mm: float | None = None) -> dict[str, Any]:
        """Catalogue lookup — real designations the model may then ask the kernel to check.

        Returns identifiers + geometry facts only (not engineering results). Honours the
        active constraints so the model never proposes an out-of-bounds section.
        """
        cap = max_depth_mm
        if self._constraints.max_depth_mm is not None:
            cap = min(cap, self._constraints.max_depth_mm) if cap else self._constraints.max_depth_mm
        allowed = self._constraints.allowed_sections
        rows: list[dict[str, Any]] = []
        for sec in self._library.by_increasing_mass():
            if allowed is not None and sec.designation not in allowed:
                continue
            if cap is not None and sec.depth_mm > cap:
                continue
            rows.append(
                {
                    "designation": sec.designation,
                    "depth_mm": round(sec.depth_mm, 1),
                    "mass_per_metre_kg_m": round(sec.mass_per_metre_kg_m, 1),
                }
            )
        return {"sections": rows, "count": len(rows)}

    def run_design(
        self,
        *,
        label: str,
        rationale: str,
        rafter_restraint_spacing_m: float | None = None,
        column_restraint_spacing_m: float | None = None,
    ) -> dict[str, Any]:
        """Auto-size the frame (kernel ``design``) under the given restraint levers."""
        try:
            raf = _clamp_spacing(rafter_restraint_spacing_m)
            col = _clamp_spacing(column_restraint_spacing_m)
        except ValueError as exc:
            return {"error": str(exc)}
        spec = self._spec_with_restraints(raf, col)
        try:
            result = design(spec, self._rate)
        except NoSectionFoundError:
            return {"error": "no section in the library satisfies this frame under these inputs"}
        except FrameUnstableError:
            return {"error": "the frame is geometrically unstable under the given loads"}
        self._record(
            label=label,
            rationale=rationale,
            mode="design",
            rafter_restraint_spacing_m=raf,
            column_restraint_spacing_m=col,
            sections=None,
            result=result,
        )
        return _observe(result)

    def run_check(
        self,
        *,
        label: str,
        rationale: str,
        rafter_designation: str,
        column_designation: str,
        rafter_restraint_spacing_m: float | None = None,
        column_restraint_spacing_m: float | None = None,
    ) -> dict[str, Any]:
        """Verify a specific rafter+column pair (kernel ``check``) under the given levers."""
        for des in (rafter_designation, column_designation):
            err = self._section_allowed(des)
            if err is not None:
                return {"error": err}
        try:
            raf = _clamp_spacing(rafter_restraint_spacing_m)
            col = _clamp_spacing(column_restraint_spacing_m)
        except ValueError as exc:
            return {"error": str(exc)}
        spec = self._spec_with_restraints(raf, col)
        sections = [
            SectionChoice(member="rafter", designation=rafter_designation),
            SectionChoice(member="column", designation=column_designation),
        ]
        try:
            result = check(spec, sections, self._rate)
        except (KeyError, ValueError) as exc:
            return {"error": f"invalid sections: {exc}"}
        except FrameUnstableError:
            return {"error": "the frame is geometrically unstable under the given loads"}
        self._record(
            label=label,
            rationale=rationale,
            mode="check",
            rafter_restraint_spacing_m=raf,
            column_restraint_spacing_m=col,
            sections=sections,
            result=result,
        )
        return _observe(result)

    def _record(self, **kw: Any) -> None:
        cand = _Candidate(
            label=_safe_prose(kw["label"], kw["mode"]),
            rationale=_safe_prose(kw["rationale"], ""),
            mode=kw["mode"],
            rafter_restraint_spacing_m=kw["rafter_restraint_spacing_m"],
            column_restraint_spacing_m=kw["column_restraint_spacing_m"],
            sections=kw["sections"],
            result=kw["result"],
        )
        key = cand.key()
        if any(c.key() == key for c in self.candidates):
            return  # identical inputs already explored
        if len(self.candidates) >= MAX_CANDIDATES:
            raise AgentBudgetError
        self.candidates.append(cand)


def _observe(result: DesignResult) -> dict[str, Any]:
    """A compact, kernel-only observation of a design result (fed back to the model)."""
    gov = max(result.checks, key=lambda c: c.utilisation, default=None)
    sections = {s.member: s.designation for s in result.sections}
    obs: dict[str, Any] = {
        "passed": result.passed,
        "governing_utilisation": round(result.governing_utilisation, 3),
        "rafter": sections.get("rafter"),
        "column": sections.get("column"),
    }
    if gov is not None:
        obs["governing_check"] = gov.name
        obs["governing_clause"] = gov.clause
    if result.total_steel_mass_kg is not None:
        obs["total_steel_mass_kg"] = round(result.total_steel_mass_kg, 1)
    return obs


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #

_SYSTEM_PROMPT = (
    "You are a structural-steel design ASSISTANT for single-bay SANS portal frames. You do "
    "NOT design anything yourself and you NEVER state an engineering number. A deterministic, "
    "code-checked kernel does all the engineering; a registered engineer signs the result.\n\n"
    "Your job: explore whether a BETTER design exists than the current one, by proposing inputs "
    "to try, and let the kernel compute the outcome. Each step you choose ONE tool:\n"
    "  - list_sections: see real section designations you may ask the kernel to check (optionally "
    "filtered by max_depth_mm).\n"
    "  - run_design: auto-size the frame, optionally changing the rafter/column restraint spacing "
    "(metres). Tighter restraint lets a lighter member pass, but needs more purlins/girts.\n"
    "  - run_check: verify a specific rafter + column section pair (use real designations from "
    "list_sections). Use this to honour stock-section or depth constraints.\n"
    "  - stop: finish when you have explored the worthwhile options.\n\n"
    "ABSOLUTE RULES:\n"
    "1. NEVER write a number (no digits) in `label` or `rationale`. Put numeric levers ONLY in "
    "their dedicated fields (e.g. rafter_restraint_spacing_m). The kernel returns all results.\n"
    "2. Only propose sections that exist (call list_sections first if unsure).\n"
    "3. Respect any stated constraints (stock sections, maximum depth).\n"
    "4. Be efficient: a handful of well-chosen experiments, then stop. Do not repeat an "
    "experiment you have already run.\n"
    "5. You cannot skip or disable a check — the kernel always runs the full set."
)


def _deterministic_proposer_disabled(_transcript: list[dict[str, Any]]) -> AgentAction:
    """A proposer that immediately stops (used when no model is available)."""
    return AgentAction(tool="stop")


def run_design_agent(
    spec: FrameSpec,
    *,
    cost_rate_zar_per_kg: float | None = None,
    constraints: AgentConstraints | None = None,
    proposer: Proposer | None = None,
    library: SectionLibrary | None = None,
    max_actions: int = MAX_ACTIONS,
) -> AgentDesignOutcome:
    """Run the bounded agentic design loop and assemble a deterministic outcome.

    Parameters
    ----------
    spec : the confirmed, validated frame.
    cost_rate_zar_per_kg : indicative steel cost rate (defaults to the kernel default).
    constraints : optional engineer constraints (stock sections / max depth).
    proposer : the model driver (injected for tests). None => baseline-only (no model).
    library : section library (injected for tests); defaults to the SAISC default.
    max_actions : hard cap on tool calls (defence-in-depth alongside the route timeout).

    The baseline plain design is always computed first and always a candidate, so the
    outcome can never be worse than today. Selection and costing are deterministic.
    """
    rate = cost_rate_zar_per_kg if cost_rate_zar_per_kg is not None else DEFAULT_COST_RATE_ZAR_PER_KG
    constraints = constraints or AgentConstraints()
    tools = KernelDesignTools(
        spec, cost_rate_zar_per_kg=rate, constraints=constraints, library=library
    )
    notes: list[str] = []

    # --- Baseline (plain deterministic design — current behaviour) -------- #
    baseline: DesignResult | None = None
    baseline_note: str | None = None
    try:
        baseline = design(spec, rate)
    except NoSectionFoundError:
        baseline_note = (
            "The standard auto-sizer could not find a single library section deep enough for "
            "this frame. The options below explore whether tighter restraint or a constrained "
            "section closes it; if not, a deeper or built-up member is an engineer decision."
        )
    except FrameUnstableError:
        baseline_note = "The frame is geometrically unstable under the given loads."

    # The baseline is itself a candidate (only when it honours any active constraints, so a
    # constrained recommendation never points at a non-compliant section).
    if baseline is not None and _result_satisfies(baseline, constraints, tools):
        tools.candidates.append(
            _Candidate(
                label="Standard design",
                rationale="The deterministic auto-sizer's lightest passing design.",
                mode="design",
                rafter_restraint_spacing_m=spec.restraints.rafter_restraint_spacing_m,
                column_restraint_spacing_m=spec.restraints.column_restraint_spacing_m,
                sections=None,
                result=baseline,
            )
        )

    # --- Model-driven exploration ---------------------------------------- #
    used_llm = False
    if proposer is not None:
        used_llm = _drive_loop(tools, proposer, constraints, notes, max_actions)
    else:
        notes.append("AI exploration unavailable — showing the standard design only.")

    if constraints.is_active():
        notes.append("Constraints applied: only options satisfying them are shown.")
    if any(_has_wind_advisory(c.result) for c in tools.candidates) or (
        baseline is not None and _has_wind_advisory(baseline)
    ):
        notes.append(
            "Wind effects are reported as advisory only (the wind-on-frame method awaits "
            "engineer validation) — they do not drive the sizing here."
        )

    return _assemble(baseline, baseline_note, tools, notes, used_llm, constraints)


def _drive_loop(
    tools: KernelDesignTools,
    proposer: Proposer,
    constraints: AgentConstraints,
    notes: list[str],
    max_actions: int,
) -> bool:
    """Execute up to *max_actions* model-chosen tool calls. Returns whether the model ran."""
    transcript: list[dict[str, Any]] = [
        {"role": "task", "content": _task_brief(tools, constraints)}
    ]
    used = False
    for _ in range(max_actions):
        try:
            action = proposer(transcript)
        except Exception:  # noqa: BLE001 — any model/transport failure degrades gracefully
            notes.append("AI exploration ended early (the assistant was unavailable).")
            break
        used = True
        if action.tool == "stop":
            break
        try:
            observation = _dispatch(tools, action)
        except AgentBudgetError:
            notes.append("Reached the exploration limit — showing the best options found.")
            break
        transcript.append(
            {"role": "action", "tool": action.tool, "label": action.label}
        )
        transcript.append({"role": "observation", "content": observation})
    return used


def _dispatch(tools: KernelDesignTools, action: AgentAction) -> dict[str, Any]:
    """Route an :class:`AgentAction` to the matching kernel tool."""
    if action.tool == "list_sections":
        return tools.list_sections(max_depth_mm=action.max_depth_mm)
    if action.tool == "run_design":
        return tools.run_design(
            label=action.label,
            rationale=action.rationale,
            rafter_restraint_spacing_m=action.rafter_restraint_spacing_m,
            column_restraint_spacing_m=action.column_restraint_spacing_m,
        )
    if action.tool == "run_check":
        if not action.rafter_designation or not action.column_designation:
            return {"error": "run_check needs both rafter_designation and column_designation"}
        return tools.run_check(
            label=action.label,
            rationale=action.rationale,
            rafter_designation=action.rafter_designation,
            column_designation=action.column_designation,
            rafter_restraint_spacing_m=action.rafter_restraint_spacing_m,
            column_restraint_spacing_m=action.column_restraint_spacing_m,
        )
    return {"error": f"unknown tool {action.tool!r}"}


def _task_brief(tools: KernelDesignTools, constraints: AgentConstraints) -> str:
    g = tools._spec.geometry
    parts = [
        f"Frame: span {g.span_m:g} m, eaves {g.eaves_height_m:g} m, pitch {g.roof_pitch_deg:g} deg, "
        f"bays {g.number_of_bays:d} at {g.bay_spacing_m:g} m.",
    ]
    if constraints.allowed_sections:
        parts.append("Only these sections may be used: " + ", ".join(constraints.allowed_sections))
    if constraints.max_depth_mm is not None:
        parts.append(f"No member may be deeper than {constraints.max_depth_mm:g} mm.")
    parts.append("Explore whether a better design exists, then stop.")
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Deterministic assembly + selection
# --------------------------------------------------------------------------- #


def _result_satisfies(
    result: DesignResult, constraints: AgentConstraints, tools: KernelDesignTools
) -> bool:
    """True if *result*'s chosen sections honour the active constraints."""
    if not constraints.is_active():
        return True
    for sc in result.sections:
        if tools._section_allowed(sc.designation) is not None:
            return False
    return True


def _has_wind_advisory(result: DesignResult) -> bool:
    return any(c.informational for c in result.checks)


def _mass(result: DesignResult) -> float | None:
    return result.total_steel_mass_kg


def _assemble(
    baseline: DesignResult | None,
    baseline_note: str | None,
    tools: KernelDesignTools,
    notes: list[str],
    used_llm: bool,
    constraints: AgentConstraints,
) -> AgentDesignOutcome:
    """Turn the collected candidates into the final outcome — deterministically.

    The baseline is excluded from the alternatives list (it is surfaced separately); the
    recommendation is chosen by reading kernel masses, never by the model.
    """
    baseline_mass = _mass(baseline) if baseline is not None else None

    alternatives: list[AgentAlternative] = []
    for cand in tools.candidates:
        # Skip the entry that is identical to the baseline standard design.
        if (
            baseline is not None
            and cand.mode == "design"
            and cand.sections is None
            and cand.rafter_restraint_spacing_m
            == baseline.frame_spec.restraints.rafter_restraint_spacing_m
            and cand.column_restraint_spacing_m
            == baseline.frame_spec.restraints.column_restraint_spacing_m
        ):
            continue
        mass = _mass(cand.result)
        delta = (
            round(mass - baseline_mass, 1)
            if (mass is not None and baseline_mass is not None)
            else None
        )
        alternatives.append(
            AgentAlternative(
                label=cand.label,
                rationale=cand.rationale,
                mode=cand.mode,
                rafter_restraint_spacing_m=cand.rafter_restraint_spacing_m,
                column_restraint_spacing_m=cand.column_restraint_spacing_m,
                sections=cand.sections,
                result=cand.result,
                mass_delta_kg=delta,
                trade_off_note=_trade_off_note(cand, baseline),
            )
        )

    recommended_index = _recommend(baseline, alternatives, constraints)
    narrative = _narrative(baseline, baseline_note, alternatives, recommended_index, constraints)

    return AgentDesignOutcome(
        baseline=baseline,
        baseline_note=baseline_note,
        alternatives=alternatives,
        recommended_index=recommended_index,
        narrative=narrative,
        notes=notes,
        used_llm=used_llm,
    )


def _trade_off_note(cand: _Candidate, baseline: DesignResult | None) -> str:
    """A deterministic, kernel-derived description of what this option trades."""
    bits: list[str] = []
    if cand.rafter_restraint_spacing_m is not None:
        bits.append(f"rafter braced every {cand.rafter_restraint_spacing_m:g} m")
    if cand.column_restraint_spacing_m is not None:
        bits.append(f"column braced every {cand.column_restraint_spacing_m:g} m")
    lever = ("Needs " + " and ".join(bits) + ". ") if bits else ""
    mass = _mass(cand.result)
    base_mass = _mass(baseline) if baseline is not None else None
    if mass is not None and base_mass is not None:
        diff = mass - base_mass
        if abs(diff) < 0.5:
            steel = "Same frame steel as the standard design."
        elif diff < 0:
            steel = f"{abs(diff):.0f} kg lighter than the standard design."
        else:
            steel = f"{diff:.0f} kg heavier than the standard design."
    else:
        steel = ""
    return (lever + steel).strip()


def _recommend(
    baseline: DesignResult | None,
    alternatives: list[AgentAlternative],
    constraints: AgentConstraints,
) -> int | None:
    """Pick the recommended option deterministically (None => recommend the baseline).

    - If the baseline could not close, recommend the lightest passing alternative (the
      agent rescued a dead-end — a genuine, trade-off-free win).
    - If constraints are active, recommend the lightest passing option (within the
      engineer's own constraint, lightest-valid is the right pick).
    - Otherwise recommend the BASELINE: tighter-restraint options save member steel but
      add purlins/girts, so we never silently claim that as a free optimisation — we
      present the options and let the engineer choose.
    """
    passing = [
        (i, a)
        for i, a in enumerate(alternatives)
        if a.result.passed and a.result.total_steel_mass_kg is not None
    ]
    if baseline is None:
        if not passing:
            return None
        return min(passing, key=lambda ia: ia[1].result.total_steel_mass_kg or 0.0)[0]
    if constraints.is_active():
        # Compare alternatives against the baseline mass; recommend baseline (None) only if
        # nothing strictly lighter passes within the constraint.
        base_mass = baseline.total_steel_mass_kg
        lighter = [
            ia
            for ia in passing
            if base_mass is None or (ia[1].result.total_steel_mass_kg or 0.0) < base_mass - 0.5
        ]
        if not lighter:
            return None
        return min(lighter, key=lambda ia: ia[1].result.total_steel_mass_kg or 0.0)[0]
    return None


def _narrative(
    baseline: DesignResult | None,
    baseline_note: str | None,
    alternatives: list[AgentAlternative],
    recommended_index: int | None,
    constraints: AgentConstraints,
) -> str:
    """Plain-language summary — every number kernel-derived."""
    if baseline is None:
        if any(a.result.passed for a in alternatives):
            return (
                "The standard auto-sizer could not close this frame, but the exploration found "
                "at least one option that passes — see the recommended option below. A registered "
                "engineer must verify it."
            )
        return (
            (baseline_note or "This frame could not be closed with the available sections.")
            + " A registered engineer should review the geometry or consider a deeper/built-up "
            "member."
        )

    rafter = next((s.designation for s in baseline.sections if s.member == "rafter"), "n/a")
    column = next((s.designation for s in baseline.sections if s.member == "column"), "n/a")
    status = "passes" if baseline.passed else "does not pass"
    mass = baseline.total_steel_mass_kg
    mass_txt = f" at about {mass:.0f} kg of frame steel" if mass is not None else ""
    lead = (
        f"The standard design uses {rafter} rafters and {column} columns{mass_txt}, and {status} "
        f"all gating code checks (governing utilisation {baseline.governing_utilisation:.2f})."
    )
    if not alternatives:
        return lead + " No better option was found, so the standard design stands."
    if recommended_index is not None:
        rec = alternatives[recommended_index]
        return (
            lead
            + f" Within your constraints, the recommended option ({rec.label}) is "
            + (rec.trade_off_note or "shown below")
            + ". A registered engineer must verify whichever option is chosen."
        )
    return (
        lead
        + f" {len(alternatives)} alternative option(s) are shown with their trade-offs — each "
        "saves member steel only by adding restraint, so the choice is yours; the standard design "
        "remains the safe default. A registered engineer must verify whichever is chosen."
    )


# --------------------------------------------------------------------------- #
# Production proposer — the OpenAI model, wrapped
# --------------------------------------------------------------------------- #


class OpenAIProposer:
    """A :class:`Proposer` backed by an OpenAI client (Structured Outputs -> AgentAction).

    Stateless per call: the full (tiny) transcript is replayed each step, mirroring the
    other AI surfaces (parsing/narrative). Any transport/parse failure raises, which the
    loop catches and degrades to the baseline.
    """

    def __init__(self, client: Any, model: str, *, max_output_tokens: int = 512) -> None:
        self._client = client
        self._model = model
        self._cap = max_output_tokens

    def __call__(self, transcript: list[dict[str, Any]]) -> AgentAction:
        import json

        extra: dict[str, Any] = (
            {"max_output_tokens": self._cap} if self._cap and self._cap > 0 else {}
        )
        response = self._client.responses.parse(
            model=self._model,
            input=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(transcript, default=str)},
            ],
            text_format=AgentAction,
            **extra,
        )
        action = getattr(response, "output_parsed", None)
        if action is None:
            return AgentAction(tool="stop")
        return action
