"""Task 4.3 — POST /parse route tests.

Wires the Phase 3 parsing layer behind an authenticated endpoint. A fake OpenAI
client is injected (no network / key), so the four outcomes (complete /
needs_clarification / invalid / out_of_scope) and the auth/config guards are tested
deterministically.

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_parse_route.py -q
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import jwt
from fastapi.testclient import TestClient
from torenone_ai import FrameSpecExtraction
from torenone_kernel.models.enums import TerrainCategory
from torenone_service.ai_runtime import AIRuntime
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": "user-1", "email": "e@firm.co.za", "aud": "authenticated",
         "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


class _FakeAIClient:
    """Returns a canned FrameSpecExtraction from responses.parse()."""

    def __init__(self, parsed: Any) -> None:
        class _Responses:
            def parse(self, **kwargs: Any) -> Any:
                return SimpleNamespace(output_parsed=parsed)

        self.responses = _Responses()


def _complete_extraction(**overrides: Any) -> FrameSpecExtraction:
    base: dict[str, Any] = dict(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0, bay_spacing_m=6.0,
        number_of_bays=5, roof_dead_load_kpa=0.20, basic_wind_speed_ms=36.0,
        terrain_category=TerrainCategory.B,
    )
    base.update(overrides)
    return FrameSpecExtraction(**base)


def _client(parsed: Any) -> TestClient:
    runtime = AIRuntime(client=_FakeAIClient(parsed), model="gpt-5.5")
    return TestClient(create_app(auth_config=AUTH, ai_runtime=runtime))


# ---------------------------------------------------------------------------
# 1. Complete description -> status complete + spec
# ---------------------------------------------------------------------------


class TestComplete:
    def test_complete_returns_spec(self):
        resp = _client(_complete_extraction()).post(
            "/parse", json={"description": "15 m span shed, 5 m eaves, 8 deg, ..."},
            headers=_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "complete"
        assert body["spec"]["geometry"]["span_m"] == 15.0
        assert body["questions"] == []

    def test_complete_lists_assumptions(self):
        body = _client(_complete_extraction()).post(
            "/parse", json={"description": "x"}, headers=_headers()
        ).json()
        fields = {a["field"] for a in body["assumptions"]}
        assert "materials.steel_grade" in fields
        # assumption values are JSON-friendly scalars
        steel = next(a for a in body["assumptions"] if a["field"] == "materials.steel_grade")
        assert steel["value"] == "S355JR"


# ---------------------------------------------------------------------------
# 2. Incomplete -> needs_clarification + questions
# ---------------------------------------------------------------------------


class TestNeedsClarification:
    def test_missing_fields_yield_questions(self):
        body = _client(FrameSpecExtraction()).post(
            "/parse", json={"description": "a shed"}, headers=_headers()
        ).json()
        assert body["status"] == "needs_clarification"
        assert body["spec"] is None
        assert len(body["questions"]) == 8
        assert "geometry.span_m" in body["missing"]

    def test_terrain_question_has_options(self):
        body = _client(_complete_extraction(terrain_category=None)).post(
            "/parse", json={"description": "x"}, headers=_headers()
        ).json()
        terrain = next(q for q in body["questions"] if q["field"] == "wind.terrain_category")
        assert terrain["options"] == ["A", "B", "C", "D"]


# ---------------------------------------------------------------------------
# 3. Invalid stated values -> status invalid + errors
# ---------------------------------------------------------------------------


class TestInvalid:
    def test_out_of_range_pitch_is_invalid(self):
        body = _client(_complete_extraction(roof_pitch_deg=80.0)).post(
            "/parse", json={"description": "x"}, headers=_headers()
        ).json()
        assert body["status"] == "invalid"
        assert body["spec"] is None
        assert body["errors"]


# ---------------------------------------------------------------------------
# 4. Out-of-scope -> refuse with note, no questions
# ---------------------------------------------------------------------------


class TestOutOfScope:
    def test_out_of_scope_refused(self):
        parsed = FrameSpecExtraction(in_scope=False, out_of_scope_reason="a steel bridge")
        body = _client(parsed).post(
            "/parse", json={"description": "design a bridge"}, headers=_headers()
        ).json()
        assert body["status"] == "out_of_scope"
        assert body["scope_note"] == "a steel bridge"
        assert body["questions"] == []
        assert body["spec"] is None


# ---------------------------------------------------------------------------
# 5. Auth + config guards
# ---------------------------------------------------------------------------


class TestGuards:
    def test_requires_auth(self):
        resp = _client(_complete_extraction()).post(
            "/parse", json={"description": "x"}
        )
        assert resp.status_code == 401

    def test_auth_checked_before_ai_runtime(self):
        """Unauthenticated request is 401 even when AI is unconfigured."""
        app = create_app(auth_config=AUTH, ai_runtime=None)
        app.state.ai_runtime = None
        resp = TestClient(app).post("/parse", json={"description": "x"})
        assert resp.status_code == 401

    def test_503_when_ai_unconfigured(self):
        app = create_app(auth_config=AUTH, ai_runtime=None)
        app.state.ai_runtime = None
        resp = TestClient(app).post("/parse", json={"description": "x"}, headers=_headers())
        assert resp.status_code == 503

    def test_empty_description_422(self):
        resp = _client(_complete_extraction()).post(
            "/parse", json={"description": ""}, headers=_headers()
        )
        assert resp.status_code == 422

    def test_missing_body_422(self):
        resp = _client(_complete_extraction()).post("/parse", json={}, headers=_headers())
        assert resp.status_code == 422


class TestRateLimit:
    def test_parse_is_rate_limited(self, monkeypatch):
        # Drop the /parse limit to 1/minute, then a 2nd authenticated call → 429.
        import torenone_service.app as app_module

        monkeypatch.setattr(app_module, "PARSE_RATE_LIMIT", "1/minute")
        client = _client(_complete_extraction())
        first = client.post("/parse", json={"description": "x"}, headers=_headers())
        assert first.status_code == 200
        second = client.post("/parse", json={"description": "x"}, headers=_headers())
        assert second.status_code == 429
