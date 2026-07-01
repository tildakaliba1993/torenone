"""POST /compare-spans route tests — clear-span vs multi-span (topology, Path B increment 6).

Mirrors /compare-layouts: same auth + spec validation, no PDF. Confirms the endpoint returns the
width-splits ranked by steel and flags multi-span options PROVISIONAL.

Run:
    PYTHONPATH="kernel/src:tools:service/src" .venv/bin/pytest service/tests/test_compare_spans_route.py -q
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
    Restraints,
    WindContext,
)
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig

SECRET = "test-supabase-jwt-secret-0123456789"
AUTH = AuthConfig(secret=SECRET)

SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=24.0, eaves_height_m=6.0, roof_pitch_deg=8.0,
        bay_spacing_m=6.0, number_of_bays=4, number_of_spans=1,  # 24 m wide
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    restraints=Restraints(rafter_restraint_spacing_m=1.5, column_restraint_spacing_m=2.0),
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


def test_returns_ranked_span_splits() -> None:
    resp = _client().post("/compare-spans", json=_body(), headers=_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["building_width_m"] == 24.0
    assert body["baseline_spans"] == 1
    spans = {o["number_of_spans"] for o in body["options"]}
    assert spans == {1, 2, 3}
    # Multi-span options are flagged provisional; the clear span is not.
    for o in body["options"]:
        assert o["provisional"] == (o["number_of_spans"] > 1)
    masses = [o["total_primary_mass_kg"] for o in body["options"] if o["total_primary_mass_kg"]]
    assert masses == sorted(masses)


def test_requires_auth() -> None:
    resp = _client().post("/compare-spans", json=_body())
    assert resp.status_code == 401
