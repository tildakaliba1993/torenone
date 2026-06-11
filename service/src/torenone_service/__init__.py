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
from torenone_service.design_service import DesignError, run_design
from torenone_service.reports import (
    InMemoryReportStore,
    ReportBuilder,
    ReportStore,
    WeasyPrintReportBuilder,
)
from torenone_service.schemas import (
    DesignRequest,
    DesignResponse,
    ParseRequest,
    ParseResponse,
    StoredReport,
)

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
    # Design (Task 4.4)
    "DesignRequest",
    "DesignResponse",
    "StoredReport",
    "run_design",
    "DesignError",
    "ReportBuilder",
    "ReportStore",
    "WeasyPrintReportBuilder",
    "InMemoryReportStore",
]
