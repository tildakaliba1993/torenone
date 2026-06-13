"""Asymmetric (ES256 / JWKS) token verification — Supabase's default signing.

The signing key is resolved from the project JWKS in production; here we generate
an EC P-256 keypair and stub :func:`_signing_key` so the tests need no network.
"""

from __future__ import annotations

import datetime as dt

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from torenone_service.auth import AuthConfig, AuthError, decode_token

_ISSUER = "https://ref.supabase.co/auth/v1"
_JWKS = "https://ref.supabase.co/auth/v1/.well-known/jwks.json"


@pytest.fixture
def keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


@pytest.fixture
def es256_config() -> AuthConfig:
    return AuthConfig(secret=None, jwks_url=_JWKS, issuer=_ISSUER, audience="authenticated")


def _token(private_key, **overrides) -> str:
    now = dt.datetime.now(tz=dt.UTC)
    claims = {
        "sub": "user-123",
        "aud": "authenticated",
        "iss": _ISSUER,
        "role": "authenticated",
        "email": "eng@firm.co.za",
        "iat": now,
        "exp": now + dt.timedelta(hours=1),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="ES256")


class TestEs256Verification:
    def test_valid_es256_token_is_accepted(self, monkeypatch, keypair, es256_config):
        private_key, public_key = keypair
        monkeypatch.setattr("torenone_service.auth._signing_key", lambda url, token: public_key)
        user = decode_token(_token(private_key), es256_config)
        assert user.user_id == "user-123"
        assert user.email == "eng@firm.co.za"
        assert user.role == "authenticated"

    def test_wrong_issuer_is_rejected(self, monkeypatch, keypair, es256_config):
        private_key, public_key = keypair
        monkeypatch.setattr("torenone_service.auth._signing_key", lambda url, token: public_key)
        token = _token(private_key, iss="https://evil.example.com/auth/v1")
        with pytest.raises(AuthError):
            decode_token(token, es256_config)

    def test_expired_token_is_rejected(self, monkeypatch, keypair, es256_config):
        private_key, public_key = keypair
        monkeypatch.setattr("torenone_service.auth._signing_key", lambda url, token: public_key)
        past = dt.datetime.now(tz=dt.UTC) - dt.timedelta(hours=2)
        token = _token(private_key, iat=past, exp=past + dt.timedelta(minutes=5))
        with pytest.raises(AuthError):
            decode_token(token, es256_config)

    def test_wrong_audience_is_rejected(self, monkeypatch, keypair, es256_config):
        private_key, public_key = keypair
        monkeypatch.setattr("torenone_service.auth._signing_key", lambda url, token: public_key)
        with pytest.raises(AuthError):
            decode_token(_token(private_key, aud="anon"), es256_config)

    def test_hs256_token_rejected_when_only_jwks_configured(self, es256_config):
        # No shared secret configured: an HS-signed token must not be accepted.
        token = jwt.encode(
            {"sub": "x", "aud": "authenticated", "exp": dt.datetime.now(tz=dt.UTC) + dt.timedelta(hours=1)},
            "some-secret",
            algorithm="HS256",
        )
        with pytest.raises(AuthError):
            decode_token(token, es256_config)


class TestFromEnvAsymmetric:
    def test_derives_jwks_and_issuer_from_supabase_url(self) -> None:
        cfg = AuthConfig.from_env({"SUPABASE_URL": "https://ref.supabase.co"})
        assert cfg.jwks_url == _JWKS
        assert cfg.issuer == _ISSUER
        assert cfg.secret is None

    def test_secret_and_url_can_coexist(self) -> None:
        cfg = AuthConfig.from_env(
            {"SUPABASE_URL": "https://ref.supabase.co/", "SUPABASE_JWT_SECRET": "legacy"}
        )
        assert cfg.jwks_url == _JWKS
        assert cfg.secret == "legacy"
