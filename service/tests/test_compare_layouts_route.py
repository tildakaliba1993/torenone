"""POST /compare-layouts route tests — topology Path A (ways to frame the building).

Proves the endpoint re-frames the same building with different bay counts, designs each through the
kernel, and returns them ranked by total primary steel — reusing the same auth + spec-validation as
/design. No PDF, no report store needed.

Run:
    PYTHONPATH="kernel/src:tools:service/src" .venv/bin/pytest service/tests/test_compare_layouts_route.py -q
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi.testclient import TestClient
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)

SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
        bay_spacing_m=6.0, number_of_bays=5,  # 30 m building
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)


def _headers() -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {"sub": "u1", "email": "e@firm.co.za", "aud": "authenticated", "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _client() -> TestClient:
    return TestClient(create_app(auth_config=AUTH))


def _body(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {"spec": SPEC.model_dump(mode="json")}
    base.update(overrides)
    return base


def test_returns_ranked_layout_options() -> None:
    resp = _client().post("/compare-layouts", json=_body(), headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["building_length_m"] == 30.0
    assert body["baseline_bays"] == 5
    bays = {o["number_of_bays"] for o in body["options"]}
    assert bays == {4, 5, 6}

    # Ranked lightest-first by total primary steel; each carries its designed sections + frame count.
    masses = [o["total_primary_mass_kg"] for o in body["options"] if o["total_primary_mass_kg"]]
    assert masses == sorted(masses)
    for o in body["options"]:
        assert o["number_of_frames"] == o["number_of_bays"] + 1
        if o["feasible"]:
            assert len(o["sections"]) >= 1
    assert body["lightest_passing_bays"] in (4, 5, 6)
    assert any("primary" in n.lower() for n in body["notes"])


def test_accepts_cost_rate_override() -> None:
    resp = _client().post(
        "/compare-layouts", json=_body(cost_rate_zar_per_kg=42.0), headers=_headers()
    )
    assert resp.status_code == 200


def test_requires_auth() -> None:
    resp = _client().post("/compare-layouts", json=_body())
    assert resp.status_code == 401
