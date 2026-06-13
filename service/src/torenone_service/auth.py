"""Supabase JWT verification (Task 4.2; asymmetric-key support added later).

Every protected route depends on :func:`require_user`, which verifies the bearer
token Supabase issued to the signed-in user — checking signature, expiry and
audience (``authenticated``).

Supabase signs user access tokens with **asymmetric keys (ES256)** by default;
these are verified against the project's public **JWKS**
(``<SUPABASE_URL>/auth/v1/.well-known/jwks.json``). Projects still using the
legacy shared secret are verified with **HS256** against ``SUPABASE_JWT_SECRET``.
The token header's ``alg`` selects the path, and each path only accepts its own
algorithm family (no alg-confusion).

Security:
  * the secret is read from the server-side environment only and is redacted in any
    representation of :class:`AuthConfig`;
  * rejection responses carry a generic reason (no token internals / secret leak).
"""

from __future__ import annotations

import dataclasses
import os
import threading
from collections.abc import Mapping
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

ENV_JWT_SECRET = "SUPABASE_JWT_SECRET"
ENV_JWT_AUD = "SUPABASE_JWT_AUD"
ENV_SUPABASE_URL = "SUPABASE_URL"
DEFAULT_AUDIENCE = "authenticated"

# Asymmetric algorithms accepted on the JWKS path (Supabase uses ES256).
ASYMMETRIC_ALGORITHMS: tuple[str, ...] = ("ES256", "ES384", "ES512", "RS256", "RS384", "RS512")


class MissingJWTSecretError(RuntimeError):
    """Raised when neither a JWT secret nor a Supabase URL (for JWKS) is configured."""


class AuthError(Exception):
    """A token failed verification. Carries a short, safe reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _redact(secret: str | None) -> str:
    if not secret:
        return "<unset>"
    return f"***{secret[-4:]}" if len(secret) > 8 else "***"


# Cache one PyJWKClient per JWKS URL (it caches the fetched keys internally).
_jwk_clients: dict[str, jwt.PyJWKClient] = {}
_jwk_lock = threading.Lock()


def _signing_key(jwks_url: str, token: str) -> Any:
    """Resolve the public signing key for *token* from the project JWKS (cached)."""
    client = _jwk_clients.get(jwks_url)
    if client is None:
        with _jwk_lock:
            client = _jwk_clients.get(jwks_url)
            if client is None:
                client = jwt.PyJWKClient(jwks_url, cache_keys=True)
                _jwk_clients[jwks_url] = client
    return client.get_signing_key_from_jwt(token).key


@dataclasses.dataclass(frozen=True, repr=False)
class AuthConfig:
    """Server-side JWT verification config. The secret is never shown in reprs."""

    secret: str | None = None
    jwks_url: str | None = None
    issuer: str | None = None
    algorithms: tuple[str, ...] = ("HS256",)
    audience: str | None = DEFAULT_AUDIENCE

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AuthConfig:
        source: Mapping[str, str] = os.environ if env is None else env
        secret = (source.get(ENV_JWT_SECRET) or "").strip() or None

        supabase_url = (source.get(ENV_SUPABASE_URL) or "").strip().rstrip("/")
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json" if supabase_url else None
        issuer = f"{supabase_url}/auth/v1" if supabase_url else None

        if not secret and not jwks_url:
            raise MissingJWTSecretError(
                f"Supabase JWT verification needs either {ENV_JWT_SECRET} (legacy HS256) "
                f"or {ENV_SUPABASE_URL} (asymmetric keys via JWKS), server-side only."
            )

        # Audience may be disabled by setting SUPABASE_JWT_AUD to an empty string.
        if ENV_JWT_AUD in source:
            audience: str | None = (source.get(ENV_JWT_AUD) or "").strip() or None
        else:
            audience = DEFAULT_AUDIENCE
        return cls(secret=secret, jwks_url=jwks_url, issuer=issuer, audience=audience)

    def __repr__(self) -> str:  # noqa: D105 — redacted on purpose
        return (
            f"AuthConfig(secret={_redact(self.secret)!r}, jwks_url={self.jwks_url!r}, "
            f"issuer={self.issuer!r}, algorithms={self.algorithms!r}, audience={self.audience!r})"
        )

    __str__ = __repr__


class AuthenticatedUser(BaseModel):
    """The verified identity of the caller (subset of Supabase JWT claims)."""

    user_id: str        # Supabase auth uid (JWT 'sub')
    email: str | None = None
    role: str | None = None


def decode_token(token: str, config: AuthConfig) -> AuthenticatedUser:
    """Verify *token* and return the authenticated user, or raise :class:`AuthError`."""
    options: Any = {"require": ["exp", "sub"]}
    decode_kwargs: dict[str, Any] = {}
    if config.audience is None:
        options["verify_aud"] = False
    else:
        decode_kwargs["audience"] = config.audience

    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.InvalidTokenError as exc:
        raise AuthError("invalid token") from exc

    try:
        if alg in config.algorithms and config.secret:
            # Legacy HS256 path — symmetric shared secret.
            key: Any = config.secret
            algorithms = list(config.algorithms)
        elif alg in ASYMMETRIC_ALGORITHMS and config.jwks_url:
            # Asymmetric path — fetch the project's public key from JWKS.
            key = _signing_key(config.jwks_url, token)
            algorithms = [alg]
            if config.issuer:
                decode_kwargs["issuer"] = config.issuer
        else:
            raise AuthError("unsupported token algorithm")

        claims = jwt.decode(token, key, algorithms=algorithms, options=options, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        # Covers bad signature, wrong audience/issuer, malformed token, missing claims.
        raise AuthError("invalid token") from exc
    except jwt.PyJWKClientError as exc:
        # JWKS key could not be resolved (unknown kid / fetch failure).
        raise AuthError("invalid token") from exc

    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise AuthError("token missing subject")

    email = claims.get("email")
    role = claims.get("role")
    return AuthenticatedUser(
        user_id=sub,
        email=email if isinstance(email, str) else None,
        role=role if isinstance(role, str) else None,
    )


_bearer = HTTPBearer(auto_error=False, description="Supabase access token")


async def require_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    """FastAPI dependency: require and return a verified user, else raise 401/503."""
    config: AuthConfig | None = getattr(request.app.state, "auth_config", None)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication is not configured",
        )
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_token(credentials.credentials, config)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.reason,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
