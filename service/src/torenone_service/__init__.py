"""TorenOne engineering service (FastAPI) — Phase 4.

Verifies Supabase JWTs, orchestrates the AI layer (torenone_ai), runs the kernel,
builds the report PDF, and persists results. This package owns HTTP/auth/IO; the
kernel stays pure.
"""

from torenone_service.app import SERVICE_NAME, SERVICE_VERSION, create_app

__version__ = SERVICE_VERSION

__all__ = ["create_app", "SERVICE_NAME", "SERVICE_VERSION", "__version__"]
