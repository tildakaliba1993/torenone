"""Conversational clarify loop — the backend half.

When a brief or drawing is incomplete, the response carries (a) the values already read (`partial`,
keyed by FrameSpecExtraction field) and (b) per-question `input_field`s. The engineer fills the gaps
and the merged values go to the DETERMINISTIC `/build-spec` (no LLM) which builds the spec.

Run:
    PYTHONPATH="kernel/src:tools:service/src" .venv/bin/pytest service/tests/test_clarify_loop.py -q
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi.testclient import TestClient
from torenone_ai import FrameSpecExtraction, build_frame_spec
from torenone_kernel.models.enums import TerrainCategory
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig
from torenone_service.schemas import ParseResponse

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)

_COMPLETE: dict[str, Any] = dict(
    span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=6.0,
    number_of_bays=5, roof_dead_load_kpa=0.2, basic_wind_speed_ms=36.0, terrain_category="B",
)


def _headers() -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u1", "email": "e@f.co", "aud": "authenticated", "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _client() -> TestClient:
    return TestClient(create_app(auth_config=AUTH, ai_runtime=None))


# --- the response now carries partial + input_field (unit) -----------------------------------

def test_incomplete_result_carries_partial_and_input_fields() -> None:
    # Read span + pitch only → the rest are questions; partial echoes what was read.
    result = build_frame_spec(FrameSpecExtraction(span_m=20.0, roof_pitch_deg=10.0))
    resp = ParseResponse.from_result(result)
    assert resp.status == "needs_clarification"
    assert resp.partial == {"span_m": 20.0, "roof_pitch_deg": 10.0}
    # Every clarify question knows which extraction field its answer fills.
    wind_q = next(q for q in resp.questions if q.field == "wind.basic_wind_speed_ms")
    assert wind_q.input_field == "basic_wind_speed_ms"
    dead_q = next(q for q in resp.questions if q.field == "dead.roof_kpa")
    assert dead_q.input_field == "roof_dead_load_kpa"  # not the leaf name


# --- /build-spec: deterministic merge --------------------------------------------------------

def test_build_spec_complete() -> None:
    resp = _client().post("/build-spec", json=_COMPLETE, headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["spec"]["geometry"]["span_m"] == 20.0


def test_build_spec_incomplete_returns_questions_and_partial() -> None:
    body = _client().post(
        "/build-spec", json={"span_m": 20.0, "terrain_category": "C"}, headers=_headers()
    ).json()
    assert body["status"] == "needs_clarification"
    assert body["spec"] is None
    assert body["partial"]["span_m"] == 20.0
    assert body["partial"]["terrain_category"] == "C"
    assert "geometry.eaves_height_m" in body["missing"]


def test_build_spec_invalid_value() -> None:
    bad = {**_COMPLETE, "roof_pitch_deg": 80.0}  # > 45 → out of range
    body = _client().post("/build-spec", json=bad, headers=_headers()).json()
    assert body["status"] == "invalid"
    assert body["errors"]


def test_build_spec_requires_auth() -> None:
    assert _client().post("/build-spec", json=_COMPLETE).status_code == 401


def test_round_trip_partial_plus_answers_completes() -> None:
    # Simulate the loop: a drawing read span/eaves/pitch/bay/bays + dead, but not wind/terrain.
    partial = dict(
        span_m=24.0, eaves_height_m=7.0, roof_pitch_deg=12.0, bay_spacing_m=6.0,
        number_of_bays=8, roof_dead_load_kpa=0.25,
    )
    first = _client().post("/build-spec", json=partial, headers=_headers()).json()
    assert first["status"] == "needs_clarification"
    answers = {q["input_field"]: ("B" if q["input_field"] == "terrain_category" else 38.0)
               for q in first["questions"]}
    merged = {**first["partial"], **answers}
    second = _client().post("/build-spec", json=merged, headers=_headers()).json()
    assert second["status"] == "complete"
    assert second["spec"]["geometry"]["span_m"] == 24.0
    assert second["spec"]["wind"]["terrain_category"] == TerrainCategory.B.value
