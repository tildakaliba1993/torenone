"""TorenOne engineering service (FastAPI) — Phase 4.

Verifies Supabase JWTs, orchestrates the AI layer (torenone_ai), runs the kernel,
builds the report PDF, and persists results. This package owns HTTP/auth/IO; the
kernel stays pure.
"""

from torenone_service.ai_runtime import AIRuntime, get_ai_runtime
from torenone_service.app import SERVICE_NAME, SERVICE_VERSION, create_app
from torenone_service.auth import (
    AuthConfig,
    AuthenticatedUser,
    MissingJWTSecretError,
    require_user,
)
from torenone_service.schemas import ParseRequest, ParseResponse

__version__ = SERVICE_VERSION

__all__ = [
    "create_app",
    "SERVICE_NAME",
    "SERVICE_VERSION",
    "__version__",
    "AuthConfig",
    "AuthenticatedUser",
    "MissingJWTSecretError",
    "require_user",
    "AIRuntime",
    "get_ai_runtime",
    "ParseRequest",
    "ParseResponse",
]
