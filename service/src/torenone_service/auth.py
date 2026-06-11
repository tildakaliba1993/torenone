"""Supabase JWT verification (Task 4.2).

Every protected route depends on :func:`require_user`, which verifies the bearer
token Supabase issued to the signed-in user. Verification is HS256 against the
project's shared JWT secret (``SUPABASE_JWT_SECRET``), checking signature, expiry,
and audience (``authenticated``).

Security:
  * the secret is read from the server-side environment only and is redacted in any
    representation of :class:`AuthConfig`;
  * rejection responses carry a generic reason (no token internals / secret leak).
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Mapping
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

ENV_JWT_SECRET = "SUPABASE_JWT_SECRET"
ENV_JWT_AUD = "SUPABASE_JWT_AUD"
DEFAULT_AUDIENCE = "authenticated"


class MissingJWTSecretError(RuntimeError):
    """Raised when ``SUPABASE_JWT_SECRET`` is absent from the server environment."""


class AuthError(Exception):
    """A token failed verification. Carries a short, safe reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _redact(secret: str) -> str:
    if not secret:
        return "<unset>"
    return f"***{secret[-4:]}" if len(secret) > 8 else "***"


@dataclasses.dataclass(frozen=True, repr=False)
class AuthConfig:
    """Server-side JWT verification config. The secret is never shown in reprs."""

    secret: str
    algorithms: tuple[str, ...] = ("HS256",)
    audience: str | None = DEFAULT_AUDIENCE

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> AuthConfig:
        source: Mapping[str, str] = os.environ if env is None else env
        secret = (source.get(ENV_JWT_SECRET) or "").strip()
        if not secret:
            raise MissingJWTSecretError(
                f"{ENV_JWT_SECRET} is not set. Supabase JWT verification needs the "
                "project's JWT secret (server-side only)."
            )
        # Audience may be disabled by setting SUPABASE_JWT_AUD to an empty string.
        if ENV_JWT_AUD in source:
            audience: str | None = (source.get(ENV_JWT_AUD) or "").strip() or None
        else:
            audience = DEFAULT_AUDIENCE
        return cls(secret=secret, audience=audience)

    def __repr__(self) -> str:  # noqa: D105 — redacted on purpose
        return (
            f"AuthConfig(secret={_redact(self.secret)!r}, algorithms={self.algorithms!r}, "
            f"audience={self.audience!r})"
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
        claims = jwt.decode(
            token,
            config.secret,
            algorithms=list(config.algorithms),
            options=options,
            **decode_kwargs,
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        # Covers bad signature, wrong audience, malformed token, missing claims.
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
