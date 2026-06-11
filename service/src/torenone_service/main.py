"""ASGI entrypoint.

Run locally with:
    uvicorn torenone_service.main:app --reload
"""

from __future__ import annotations

from torenone_service.app import create_app

app = create_app()
