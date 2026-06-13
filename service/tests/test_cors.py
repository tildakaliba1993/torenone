"""CORS is required so the browser SPA (a different origin) can call the service.

Without it, every browser request — even with a valid token — is blocked by the
same-origin policy and never reaches the route.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from torenone_service.app import create_app

_FRONTEND_ORIGIN = "http://localhost:3000"


class TestCors:
    def test_preflight_allows_the_frontend_origin(self) -> None:
        client = TestClient(create_app())
        resp = client.options(
            "/parse",
            headers={
                "Origin": _FRONTEND_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert resp.status_code in (200, 204)
        assert resp.headers.get("access-control-allow-origin") == _FRONTEND_ORIGIN

    def test_simple_request_echoes_allow_origin(self) -> None:
        client = TestClient(create_app())
        resp = client.get("/health", headers={"Origin": _FRONTEND_ORIGIN})
        assert resp.headers.get("access-control-allow-origin") == _FRONTEND_ORIGIN

    def test_unlisted_origin_is_not_allowed(self) -> None:
        client = TestClient(create_app())
        resp = client.get("/health", headers={"Origin": "https://evil.example.com"})
        assert resp.status_code == 200  # the response still returns
        assert resp.headers.get("access-control-allow-origin") != "https://evil.example.com"

    def test_origins_configurable_via_env(self, monkeypatch) -> None:
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://app.torenone.com")
        client = TestClient(create_app())
        resp = client.get("/health", headers={"Origin": "https://app.torenone.com"})
        assert resp.headers.get("access-control-allow-origin") == "https://app.torenone.com"
