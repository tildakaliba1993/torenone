"""Task 4.2 — Supabase JWT verification tests.

Deliverable: protected routes require a valid Supabase JWT — valid passes,
invalid/expired/missing rejected.

Run:
    PYTHONPATH="kernel/src:tools:service/src" \
        /opt/homebrew/opt/python@3.11/bin/python3.11 -m pytest service/tests/test_auth.py -q
"""

from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient
from torenone_service.app import create_app
from torenone_service.auth import (
    AuthConfig,
    AuthError,
    MissingJWTSecretError,
    decode_token,
)

SECRET = "test-supabase-jwt-secret-0123456789"
CONFIG = AuthConfig(secret=SECRET)


def _token(
    *,
    sub: str = "11111111-1111-1111-1111-111111111111",
    email: str = "eng@firm.co.za",
    role: str = "authenticated",
    aud: str = "authenticated",
    secret: str = SECRET,
    exp_delta: int = 3600,
    drop: tuple[str, ...] = (),
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "aud": aud,
        "iat": now,
        "exp": now + exp_delta,
    }
    for key in drop:
        payload.pop(key, None)
    return jwt.encode(payload, secret, algorithm="HS256")


def _client(config: AuthConfig | None = CONFIG) -> TestClient:
    return TestClient(create_app(auth_config=config))


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. decode_token (unit, no HTTP)
# ---------------------------------------------------------------------------


class TestDecodeToken:
    def test_valid_token_returns_user(self):
        user = decode_token(_token(), CONFIG)
        assert user.user_id == "11111111-1111-1111-1111-111111111111"
        assert user.email == "eng@firm.co.za"
        assert user.role == "authenticated"

    def test_expired_token_raises(self):
        with pytest.raises(AuthError):
            decode_token(_token(exp_delta=-10), CONFIG)

    def test_bad_signature_raises(self):
        with pytest.raises(AuthError):
            decode_token(_token(secret="wrong-secret-but-32-chars-long-xyz"), CONFIG)

    def test_wrong_audience_raises(self):
        with pytest.raises(AuthError):
            decode_token(_token(aud="some-other-aud"), CONFIG)

    def test_missing_sub_raises(self):
        with pytest.raises(AuthError):
            decode_token(_token(drop=("sub",)), CONFIG)

    def test_missing_exp_raises(self):
        with pytest.raises(AuthError):
            decode_token(_token(drop=("exp",)), CONFIG)

    def test_garbage_token_raises(self):
        with pytest.raises(AuthError):
            decode_token("not-a-jwt", CONFIG)

    def test_audience_disabled_accepts_any_aud(self):
        cfg = AuthConfig(secret=SECRET, audience=None)
        user = decode_token(_token(aud="anything"), cfg)
        assert user.user_id


# ---------------------------------------------------------------------------
# 2. Protected route /me (valid passes)
# ---------------------------------------------------------------------------


class TestProtectedRouteValid:
    def test_valid_token_allows_access(self):
        resp = _client().get("/me", headers=_auth(_token()))
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == "11111111-1111-1111-1111-111111111111"
        assert body["email"] == "eng@firm.co.za"

    def test_health_is_public(self):
        """The skeleton's health endpoint stays open (no auth)."""
        assert _client().get("/health").status_code == 200


# ---------------------------------------------------------------------------
# 3. Protected route /me (invalid/expired/missing rejected)
# ---------------------------------------------------------------------------


class TestProtectedRouteRejects:
    def test_missing_header_401(self):
        resp = _client().get("/me")
        assert resp.status_code == 401

    def test_non_bearer_scheme_401(self):
        resp = _client().get("/me", headers={"Authorization": "Basic abc123"})
        assert resp.status_code == 401

    def test_expired_token_401(self):
        resp = _client().get("/me", headers=_auth(_token(exp_delta=-5)))
        assert resp.status_code == 401

    def test_bad_signature_401(self):
        resp = _client().get("/me", headers=_auth(_token(secret="attacker-secret-32-chars-long-abcd")))
        assert resp.status_code == 401

    def test_wrong_audience_401(self):
        resp = _client().get("/me", headers=_auth(_token(aud="evil")))
        assert resp.status_code == 401

    def test_garbage_token_401(self):
        resp = _client().get("/me", headers=_auth("clearly.not.jwt"))
        assert resp.status_code == 401

    def test_rejection_does_not_leak_secret(self):
        resp = _client().get("/me", headers=_auth(_token(secret="attacker-secret-32-chars-long-abcd")))
        assert SECRET not in resp.text

    def test_www_authenticate_header_on_401(self):
        resp = _client().get("/me")
        assert resp.headers.get("WWW-Authenticate") == "Bearer"


# ---------------------------------------------------------------------------
# 4. Unconfigured auth -> 503 (and health still works)
# ---------------------------------------------------------------------------


class TestUnconfigured:
    def test_protected_route_503_when_no_secret(self):
        client = TestClient(create_app(auth_config=None))
        # Deterministically unconfigured by forcing state to None.
        client.app.state.auth_config = None  # type: ignore[attr-defined]
        resp = client.get("/me", headers=_auth(_token()))
        assert resp.status_code == 503

    def test_health_ok_when_no_secret(self):
        client = TestClient(create_app(auth_config=None))
        client.app.state.auth_config = None  # type: ignore[attr-defined]
        assert client.get("/health").status_code == 200


# ---------------------------------------------------------------------------
# 5. AuthConfig — env loading + secret redaction
# ---------------------------------------------------------------------------


class TestAuthConfig:
    def test_from_env_reads_secret(self):
        cfg = AuthConfig.from_env({"SUPABASE_JWT_SECRET": SECRET})
        assert cfg.secret == SECRET
        assert cfg.audience == "authenticated"

    def test_from_env_missing_raises(self):
        with pytest.raises(MissingJWTSecretError):
            AuthConfig.from_env({})

    def test_from_env_blank_raises(self):
        with pytest.raises(MissingJWTSecretError):
            AuthConfig.from_env({"SUPABASE_JWT_SECRET": "   "})

    def test_audience_override(self):
        cfg = AuthConfig.from_env(
            {"SUPABASE_JWT_SECRET": SECRET, "SUPABASE_JWT_AUD": "my-aud"}
        )
        assert cfg.audience == "my-aud"

    def test_audience_can_be_disabled(self):
        cfg = AuthConfig.from_env({"SUPABASE_JWT_SECRET": SECRET, "SUPABASE_JWT_AUD": ""})
        assert cfg.audience is None

    def test_repr_redacts_secret(self):
        assert SECRET not in repr(AuthConfig(secret=SECRET))
        assert "***" in repr(AuthConfig(secret=SECRET))

    def test_str_redacts_secret(self):
        assert SECRET not in str(AuthConfig(secret=SECRET))
