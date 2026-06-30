"""Tests for the agentic design loop (torenone_ai.design_agent) + POST /design-agent.

The kernel runs for real (deterministic, CI-safe). The model is a scripted fake
:class:`Proposer`, so no OpenAI key is needed and the safety guards are exercised
directly. Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /Users/cash/TorenOne/.venv/bin/pytest service/tests/test_design_agent.py -q
"""

from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from torenone_ai.design_agent import (
    MAX_CANDIDATES,
    AgentAction,
    AgentAlternative,
    AgentConstraints,
    OpenAIProposer,
    _recommend,
    run_design_agent,
)
from torenone_kernel.design import design
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_service.ai_runtime import AIRuntime
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)

SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
        bay_spacing_m=6.0, number_of_bays=5,
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)


class ScriptedProposer:
    """A fake Proposer that returns a fixed list of actions, then stops."""

    def __init__(self, *actions: AgentAction) -> None:
        self._actions = list(actions)
        self.calls = 0

    def __call__(self, _transcript: list[dict[str, Any]]) -> AgentAction:
        self.calls += 1
        if self._actions:
            return self._actions.pop(0)
        return AgentAction(tool="stop")


# --------------------------------------------------------------------------- #
# Baseline / degradation
# --------------------------------------------------------------------------- #


def test_baseline_present_without_proposer() -> None:
    """No model => still a valid baseline; deterministic seeds may add passing options."""
    out = run_design_agent(SPEC, proposer=None)
    assert out.used_llm is False
    assert out.baseline is not None
    assert out.baseline.passed is True
    # Unconstrained, the baseline stays the recommended default (no auto-recommend).
    assert out.recommended_index is None
    # Mandatory checks always ran — the baseline carries the full kernel check set.
    assert len(out.baseline.checks) > 0
    # Every surfaced alternative is a real, PASSING kernel design (never a dead end).
    assert all(a.result.passed for a in out.alternatives)


def test_seeds_produce_options_without_a_model() -> None:
    """Deterministic seed exploration makes the panel useful even with no model."""
    out = run_design_agent(SPEC, proposer=None)
    assert out.used_llm is False
    # The unconstrained restraint sweep tries tighter rafter bracing -> real options.
    assert len(out.alternatives) > 0
    assert all(a.rafter_restraint_spacing_m is not None for a in out.alternatives)
    assert all(a.result.passed for a in out.alternatives)


def test_proposer_failure_degrades_to_baseline() -> None:
    """If the model raises, the loop degrades cleanly to the baseline."""

    class Boom:
        def __call__(self, _t: list[dict[str, Any]]) -> AgentAction:
            raise RuntimeError("model down")

    out = run_design_agent(SPEC, proposer=Boom())
    assert out.used_llm is False  # raised before any action succeeded
    assert out.baseline is not None
    assert out.baseline.passed is True


# --------------------------------------------------------------------------- #
# Model-driven exploration
# --------------------------------------------------------------------------- #


def test_run_design_lever_produces_alternative() -> None:
    """A restraint-spacing experiment yields a kernel-verified alternative."""
    proposer = ScriptedProposer(
        AgentAction(
            tool="run_design",
            label="Brace the rafter more closely",
            rationale="tighter rafter restraint may allow a lighter beam",
            rafter_restraint_spacing_m=2.0,
        ),
    )
    out = run_design_agent(SPEC, proposer=proposer)
    assert out.used_llm is True
    # The model's experiment is present (deduped with any identical seed).
    alt = next(a for a in out.alternatives if a.rafter_restraint_spacing_m == 2.0)
    assert alt.mode == "design"
    assert isinstance(alt.mass_delta_kg, float)
    assert "rafter braced every 2 m" in alt.trade_off_note
    # The alternative is a real kernel result with the full check set.
    assert len(alt.result.checks) > 0


def test_model_authored_numbers_are_stripped() -> None:
    """A label/rationale containing digits must never reach the UI verbatim."""
    proposer = ScriptedProposer(
        AgentAction(
            tool="run_design",
            label="Try 2.5 m bracing",
            rationale="this should save about 200 kg of steel",
            rafter_restraint_spacing_m=2.5,  # not a seed value -> the model's text is used
        ),
    )
    out = run_design_agent(SPEC, proposer=proposer)
    # No alternative anywhere may carry a model-authored digit.
    for alt in out.alternatives:
        assert not any(ch.isdigit() for ch in alt.label)
        assert not any(ch.isdigit() for ch in alt.rationale)


def test_unknown_section_is_rejected() -> None:
    """A check on a non-existent section produces no candidate (no crash)."""
    proposer = ScriptedProposer(
        AgentAction(
            tool="run_check",
            label="try a made-up section",
            rationale="this section does not exist",
            rafter_designation="UNOBTANIUM BEAM",
            column_designation="UNOBTANIUM BEAM",
        ),
    )
    out = run_design_agent(SPEC, proposer=proposer)
    assert out.baseline is not None
    # The bad section never became a candidate (seed restraint options may still appear).
    assert all(
        a.sections is None or all(s.designation != "UNOBTANIUM BEAM" for s in a.sections)
        for a in out.alternatives
    )


def test_out_of_range_restraint_is_rejected() -> None:
    """An implausible restraint spacing is rejected, not fed to the kernel."""
    proposer = ScriptedProposer(
        AgentAction(
            tool="run_design",
            label="absurd bracing",
            rationale="way too tight",
            rafter_restraint_spacing_m=0.01,
        ),
    )
    out = run_design_agent(SPEC, proposer=proposer)
    # The absurd spacing was rejected; no alternative was built from it.
    assert all(a.rafter_restraint_spacing_m != 0.01 for a in out.alternatives)


# --------------------------------------------------------------------------- #
# Constraints
# --------------------------------------------------------------------------- #


def test_constraints_filter_list_sections() -> None:
    """list_sections only returns sections honouring the active constraints."""
    out = run_design_agent(
        SPEC,
        proposer=ScriptedProposer(AgentAction(tool="list_sections")),
        constraints=AgentConstraints(max_depth_mm=300.0),
    )
    # We can't read list_sections output directly here, but the run must complete and the
    # constraint note must be present.
    assert any("Constraints applied" in n for n in out.notes)


def test_constraint_rejects_out_of_stock_section() -> None:
    """With a stock list, a section outside it is rejected even if it exists."""
    library_designations = design(SPEC).sections
    rafter_des = next(s.designation for s in library_designations if s.member == "rafter")
    proposer = ScriptedProposer(
        AgentAction(
            tool="run_check",
            label="off-list section",
            rationale="not in stock",
            rafter_designation=rafter_des,
            column_designation=rafter_des,
        ),
    )
    out = run_design_agent(
        SPEC,
        proposer=proposer,
        constraints=AgentConstraints(allowed_sections=["IPE 200"]),  # excludes rafter_des
    )
    # rafter_des is not in the allowed list -> rejected -> no alternative.
    assert all(
        a.sections is None or all(s.designation == "IPE 200" for s in a.sections)
        for a in out.alternatives
    )


def test_seed_constraint_search_finds_within_stock_without_model() -> None:
    """The deterministic constraint search finds a passing stock pair with no model.

    Also covers the baseline-invalid case: the unconstrained baseline uses a rafter NOT in
    the stock list, so the recommendation must be a constraint-valid option, not the baseline.
    """
    raf_des = next(s.designation for s in design(SPEC).sections if s.member == "rafter")
    out = run_design_agent(
        SPEC,
        proposer=None,
        constraints=AgentConstraints(allowed_sections=[raf_des]),
    )
    assert out.recommended_index is not None
    rec = out.alternatives[out.recommended_index]
    assert rec.result.passed is True
    assert rec.sections is not None
    assert all(s.designation == raf_des for s in rec.sections)


# --------------------------------------------------------------------------- #
# Recommendation honesty (unit)
# --------------------------------------------------------------------------- #


def _alt_with_mass(result_template: Any, mass: float) -> AgentAlternative:
    res = result_template.model_copy(update={"total_steel_mass_kg": mass})
    return AgentAlternative(
        label="opt", rationale="", mode="check", result=res, mass_delta_kg=None
    )


def test_recommend_unconstrained_keeps_baseline_even_if_lighter_exists() -> None:
    """Unconstrained: a lighter restraint-traded option is NOT auto-recommended."""
    baseline = design(SPEC)
    base_mass = baseline.total_steel_mass_kg or 1000.0
    lighter = _alt_with_mass(baseline, base_mass - 100.0)
    rec = _recommend(baseline, [lighter], AgentConstraints())
    assert rec is None  # baseline stays the default; the trade-off is the engineer's call


def test_recommend_constrained_picks_lightest_passing() -> None:
    """With constraints active, the lightest passing option is recommended."""
    baseline = design(SPEC)
    base_mass = baseline.total_steel_mass_kg or 1000.0
    heavier = _alt_with_mass(baseline, base_mass + 50.0)
    lighter = _alt_with_mass(baseline, base_mass - 50.0)
    rec = _recommend(baseline, [heavier, lighter], AgentConstraints(max_depth_mm=400.0))
    assert rec == 1  # the lighter alternative


def test_recommend_constrained_baseline_when_nothing_lighter() -> None:
    baseline = design(SPEC)
    base_mass = baseline.total_steel_mass_kg or 1000.0
    heavier = _alt_with_mass(baseline, base_mass + 50.0)
    rec = _recommend(baseline, [heavier], AgentConstraints(max_depth_mm=400.0))
    assert rec is None


# --------------------------------------------------------------------------- #
# Action space is closed; budget is bounded
# --------------------------------------------------------------------------- #


def test_action_space_is_closed() -> None:
    """There is no tool to skip/disable a check — the Literal forbids unknown tools."""
    with pytest.raises(ValidationError):
        AgentAction(tool="disable_check")  # type: ignore[arg-type]


def test_budget_caps_candidates() -> None:
    """A model that keeps proposing distinct experiments is bounded, not unbounded."""

    class Greedy:
        def __init__(self) -> None:
            self.n = 0

        def __call__(self, _t: list[dict[str, Any]]) -> AgentAction:
            self.n += 1
            # Each call a unique, valid restraint spacing -> a distinct candidate.
            return AgentAction(
                tool="run_design",
                label="experiment",
                rationale="explore",
                rafter_restraint_spacing_m=1.0 + self.n * 0.2,
            )

    out = run_design_agent(SPEC, proposer=Greedy())
    # Candidates (incl. baseline) are capped; the loop terminates.
    assert len(out.alternatives) <= MAX_CANDIDATES


# --------------------------------------------------------------------------- #
# OpenAIProposer wrapper (no real network)
# --------------------------------------------------------------------------- #


class _FakeParsed:
    def __init__(self, action: AgentAction) -> None:
        self.output_parsed = action


class _FakeResponses:
    def __init__(self, action: AgentAction) -> None:
        self._action = action
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> _FakeParsed:
        self.calls.append(kwargs)
        return _FakeParsed(self._action)


class _FakeClient:
    def __init__(self, action: AgentAction) -> None:
        self.responses = _FakeResponses(action)


def test_openai_proposer_returns_parsed_action() -> None:
    client = _FakeClient(AgentAction(tool="stop"))
    proposer = OpenAIProposer(client, "gpt-test")
    action = proposer([{"role": "task", "content": "x"}])
    assert action.tool == "stop"
    assert client.responses.calls[0]["model"] == "gpt-test"


def test_openai_proposer_handles_empty_parse() -> None:
    class _EmptyResponses:
        def parse(self, **_kwargs: Any) -> Any:
            class _R:
                output_parsed = None

            return _R()

    class _EmptyClient:
        responses = _EmptyResponses()

    action = OpenAIProposer(_EmptyClient(), "gpt-test")([])
    assert action.tool == "stop"


# --------------------------------------------------------------------------- #
# Route
# --------------------------------------------------------------------------- #


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": "user-9", "email": "e@firm.co.za", "aud": "authenticated",
         "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def _spec_payload() -> dict[str, Any]:
    return SPEC.model_dump(mode="json")


def test_route_requires_auth() -> None:
    client = TestClient(create_app(auth_config=AUTH))
    resp = client.post("/design-agent", json={"spec": _spec_payload()})
    assert resp.status_code == 401


def test_route_baseline_when_ai_unavailable() -> None:
    """A failing AI client degrades the route to a baseline-only 200."""

    class _BoomResponses:
        def parse(self, **_kwargs: Any) -> Any:
            raise RuntimeError("upstream down")

    class _BoomClient:
        responses = _BoomResponses()

    runtime = AIRuntime(client=_BoomClient(), model="gpt-test")
    client = TestClient(create_app(auth_config=AUTH, ai_runtime=runtime))
    resp = client.post("/design-agent", json={"spec": _spec_payload()}, headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_llm"] is False
    assert body["baseline"] is not None
    assert body["baseline"]["passed"] is True


def test_route_runs_loop_with_fake_model() -> None:
    """The route drives the real OpenAIProposer against a fake client end-to-end."""
    runtime = AIRuntime(client=_FakeClient(AgentAction(tool="stop")), model="gpt-test")
    client = TestClient(create_app(auth_config=AUTH, ai_runtime=runtime))
    resp = client.post("/design-agent", json={"spec": _spec_payload()}, headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["used_llm"] is True
    assert body["baseline"]["passed"] is True
