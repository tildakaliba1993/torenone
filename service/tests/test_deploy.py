"""Deployment-artifact contract tests (Task 4.6).

These do **not** build the image — Docker is unavailable in the Python unit-test
environment, so the image is actually built and health-smoke-tested in the CI
``docker`` job (``.github/workflows/ci.yml``). Here we lock the *contract* of the
deploy files so the entrypoint, ``PYTHONPATH``, native PDF dependencies, non-root
execution and Fly health check cannot silently regress.

Why these specific invariants:
  * ``torenone_service`` / ``torenone_ai`` live in ``service/src`` and are **not**
    pip-packaged (only ``torenone_kernel`` is — see ``[tool.setuptools.packages.find]``),
    so the container must put ``service/src`` on ``PYTHONPATH`` or the app won't import.
  * WeasyPrint needs the Pango native library at runtime; without it ``/design`` cannot
    render a PDF (it would 502 in production while passing every Python test).
  * Python 3.11 is the only supported interpreter (``requires-python>=3.11``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def dockerfile() -> str:
    path = REPO_ROOT / "Dockerfile"
    assert path.is_file(), "Dockerfile must exist at the repo root"
    return path.read_text()


def test_dockerfile_uses_python_311(dockerfile: str) -> None:
    assert "python:3.11" in dockerfile


def test_dockerfile_installs_service_and_pdf_extras(dockerfile: str) -> None:
    # The container ships WeasyPrint (pdf extra) so /design renders real PDFs in prod.
    assert "[service,pdf]" in dockerfile


def test_dockerfile_installs_weasyprint_native_libs(dockerfile: str) -> None:
    # Pango is WeasyPrint's runtime native dep; Pillow (a Python dep) handles raster.
    assert "libpango-1.0-0" in dockerfile


def test_dockerfile_puts_service_src_on_pythonpath(dockerfile: str) -> None:
    assert "PYTHONPATH" in dockerfile
    assert "service/src" in dockerfile


def test_dockerfile_entrypoint_runs_the_asgi_app(dockerfile: str) -> None:
    assert "uvicorn" in dockerfile
    assert "torenone_service.main:app" in dockerfile
    # Must bind all interfaces so the container is reachable.
    assert "0.0.0.0" in dockerfile


def test_dockerfile_runs_as_non_root(dockerfile: str) -> None:
    assert "USER " in dockerfile


def test_dockerfile_has_healthcheck_on_health(dockerfile: str) -> None:
    assert "HEALTHCHECK" in dockerfile
    assert "/health" in dockerfile


def test_dockerignore_excludes_heavy_and_secret_paths() -> None:
    path = REPO_ROOT / ".dockerignore"
    assert path.is_file(), ".dockerignore must exist"
    text = path.read_text()
    for pattern in (".git", "web", "standards", ".env"):
        assert pattern in text, f".dockerignore should exclude {pattern}"


def test_flytoml_contract() -> None:
    path = REPO_ROOT / "fly.toml"
    assert path.is_file(), "fly.toml must exist"
    text = path.read_text()
    assert "internal_port = 8000" in text
    assert "/health" in text  # health-check path
