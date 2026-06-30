"""Task 4.5 — error-handling tests.

Typed errors, safe messages, and (critically) no secret leakage in any response.

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_errors.py -q
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi.testclient import TestClient
from openai import OpenAIError
from torenone_kernel.models.enums import TerrainCategory
from torenone_kernel.models.frame_spec import (
    DeadLoadInputs,
    FrameGeometry,
    FrameSpec,
    WindContext,
)
from torenone_kernel.models.results import DesignResult
from torenone_service.ai_runtime import AIRuntime
from torenone_service.app import create_app
from torenone_service.auth import AuthConfig
from torenone_service.errors import GENERIC_500_MESSAGE
from torenone_service.schemas import StoredReport

SECRET = "supabase-jwt-secret-DO-NOT-LEAK-123456"
FAKE_KEY = "sk-openai-DO-NOT-LEAK-abcdef0123456789"
AUTH = AuthConfig(secret=SECRET)

SPEC = FrameSpec(
    geometry=FrameGeometry(
        span_m=15.0, eaves_height_m=5.0, roof_pitch_deg=8.0,
        bay_spacing_m=6.0, number_of_bays=5,
    ),
    dead=DeadLoadInputs(roof_kpa=0.20, services_kpa=0.05),
    wind=WindContext(basic_wind_speed_ms=36.0, terrain_category=TerrainCategory.B),
)


def _token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": "user-err", "aud": "authenticated", "iat": now, "exp": now + 3600},
        SECRET, algorithm="HS256",
    )


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


class _RaisingAIClient:
    """An AI client whose responses.parse() raises a chosen exception."""

    def __init__(self, exc: Exception) -> None:
        class _Responses:
            def parse(self, **kwargs: Any) -> Any:
                raise exc

        self.responses = _Responses()


class _RaisingBuilder:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def build_pdf(self, result: DesignResult, metadata: object = None) -> bytes:
        raise self._exc


class _OkStore:
    def save_report(self, **kwargs: Any) -> StoredReport:
        return StoredReport(run_id="r", report_id="r", storage_path="p", size_bytes=1)


def _parse_client(exc: Exception, *, raise_server_exceptions: bool = True) -> TestClient:
    runtime = AIRuntime(client=_RaisingAIClient(exc), model="gpt-5.5")
    app = create_app(auth_config=AUTH, ai_runtime=runtime)
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


# ---------------------------------------------------------------------------
# 1. Upstream AI failure -> 502, safe message
# ---------------------------------------------------------------------------


class TestUpstreamAIError:
    def test_openai_error_maps_to_502(self):
        client = _parse_client(OpenAIError("upstream boom"))
        resp = client.post("/parse", json={"description": "x"}, headers=_headers())
        assert resp.status_code == 502
        assert resp.json()["detail"] == "the AI parsing service is temporarily unavailable"

    def test_openai_error_detail_not_leaked(self):
        client = _parse_client(OpenAIError(f"contains {FAKE_KEY}"))
        resp = client.post("/parse", json={"description": "x"}, headers=_headers())
        assert FAKE_KEY not in resp.text


# ---------------------------------------------------------------------------
# 2. Unexpected exception -> 500 generic (catch-all), no leak
# ---------------------------------------------------------------------------


class TestUnexpectedException:
    def test_unexpected_error_is_generic_500(self):
        client = _parse_client(
            RuntimeError("kaboom"), raise_server_exceptions=False
        )
        resp = client.post("/parse", json={"description": "x"}, headers=_headers())
        assert resp.status_code == 500
        assert resp.json() == {"detail": GENERIC_500_MESSAGE}

    def test_unexpected_error_does_not_leak_internal_text(self):
        client = _parse_client(
            RuntimeError(f"leak {SECRET} {FAKE_KEY}"), raise_server_exceptions=False
        )
        resp = client.post("/parse", json={"description": "x"}, headers=_headers())
        assert SECRET not in resp.text
        assert FAKE_KEY not in resp.text
        assert "kaboom" not in resp.text


# ---------------------------------------------------------------------------
# 3. Report generation failure -> 502, safe message
# ---------------------------------------------------------------------------


class TestReportFailure:
    def _client(self, exc: Exception) -> TestClient:
        app = create_app(
            auth_config=AUTH, report_builder=_RaisingBuilder(exc), report_store=_OkStore()
        )
        return TestClient(app)

    def _design_body(self) -> dict[str, Any]:
        return {"spec": SPEC.model_dump(mode="json"), "mode": "design"}

    def test_report_failure_maps_to_502(self):
        resp = self._client(RuntimeError("weasyprint exploded")).post(
            "/design", json=self._design_body(), headers=_headers()
        )
        assert resp.status_code == 502
        assert resp.json()["detail"] == "failed to generate or store the report"

    def test_report_failure_does_not_leak(self):
        resp = self._client(RuntimeError(f"weasyprint {SECRET}")).post(
            "/design", json=self._design_body(), headers=_headers()
        )
        assert SECRET not in resp.text


# ---------------------------------------------------------------------------
# 4. No secret ever appears in an error body (defence in depth)
# ---------------------------------------------------------------------------


class TestNoSecretLeak:
    def test_secret_absent_across_error_paths(self):
        bodies: list[str] = []

        # 401 (bad token), 502 (AI), 500 (catch-all)
        c401 = _parse_client(OpenAIError("x"))
        bodies.append(c401.post("/parse", json={"description": "x"}).text)  # no auth -> 401
        bodies.append(
            _parse_client(OpenAIError("x")).post(
                "/parse", json={"description": "x"}, headers=_headers()
            ).text
        )
        bodies.append(
            _parse_client(RuntimeError("x"), raise_server_exceptions=False).post(
                "/parse", json={"description": "x"}, headers=_headers()
            ).text
        )
        for body in bodies:
            assert SECRET not in body
            assert FAKE_KEY not in body


# ---------------------------------------------------------------------------
# 5. Regression — typed input errors still map cleanly
# ---------------------------------------------------------------------------


class TestTypedInputErrors:
    def test_design_error_is_422_with_safe_message(self):
        app = create_app(auth_config=AUTH)
        resp = TestClient(app).post(
            "/design",
            json={"spec": SPEC.model_dump(mode="json"), "mode": "check"},  # check w/o sections
            headers=_headers(),
        )
        assert resp.status_code == 422
        assert "check mode requires" in resp.json()["detail"]
