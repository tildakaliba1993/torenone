"""POST /parse-drawing route tests — the drawings-in front door.

Same wiring as /parse (fake vision client, no network/key): the four outcomes plus the
image-validation and auth guards. Proves the endpoint returns the SAME ParseResponse shape, so the
web confirm-gate is reused unchanged.

Run:
    PYTHONPATH="kernel/src:tools:service/src" .venv/bin/pytest service/tests/test_parse_drawing_route.py -q
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
_IMG = "data:image/png;base64,iVBORw0KGgo="


def _headers() -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {"sub": "user-1", "email": "e@firm.co.za", "aud": "authenticated", "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class _FakeAIClient:
    def __init__(self, parsed: Any) -> None:
        class _Responses:
            def parse(self, **kwargs: Any) -> Any:
                return SimpleNamespace(output_parsed=parsed)

        self.responses = _Responses()


def _complete_extraction(**overrides: Any) -> FrameSpecExtraction:
    base: dict[str, Any] = dict(
        span_m=20.0, eaves_height_m=6.0, roof_pitch_deg=10.0, bay_spacing_m=5.0,
        number_of_bays=8, roof_dead_load_kpa=0.15, basic_wind_speed_ms=40.0,
        terrain_category=TerrainCategory.C,
    )
    base.update(overrides)
    return FrameSpecExtraction(**base)


def _client(parsed: Any) -> TestClient:
    runtime = AIRuntime(client=_FakeAIClient(parsed), model="gpt-5.5")
    return TestClient(create_app(auth_config=AUTH, ai_runtime=runtime))


def test_complete_drawing_returns_spec() -> None:
    resp = _client(_complete_extraction()).post(
        "/parse-drawing", json={"image_data_url": _IMG, "note": "rural"}, headers=_headers()
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "complete"
    assert body["spec"]["geometry"]["span_m"] == 20.0


def test_incomplete_drawing_yields_questions() -> None:
    body = _client(FrameSpecExtraction(span_m=18.0)).post(
        "/parse-drawing", json={"image_data_url": _IMG}, headers=_headers()
    ).json()
    assert body["status"] == "needs_clarification"
    assert body["spec"] is None
    assert "geometry.eaves_height_m" in body["missing"]


def test_out_of_scope_drawing_refused() -> None:
    parsed = FrameSpecExtraction(in_scope=False, out_of_scope_reason="a steel truss")
    body = _client(parsed).post(
        "/parse-drawing", json={"image_data_url": _IMG}, headers=_headers()
    ).json()
    assert body["status"] == "out_of_scope"
    assert body["scope_note"] == "a steel truss"


def test_requires_auth() -> None:
    resp = _client(_complete_extraction()).post("/parse-drawing", json={"image_data_url": _IMG})
    assert resp.status_code == 401


def test_rejects_non_image_url() -> None:
    resp = _client(_complete_extraction()).post(
        "/parse-drawing", json={"image_data_url": "http://evil/x.exe"}, headers=_headers()
    )
    assert resp.status_code == 422  # not a data:image/* or https URL


def test_missing_image_422() -> None:
    resp = _client(_complete_extraction()).post("/parse-drawing", json={}, headers=_headers())
    assert resp.status_code == 422
