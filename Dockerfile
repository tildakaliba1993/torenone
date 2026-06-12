# TorenOne engineering service (FastAPI) — production container (Task 4.6).
#
# Two stages:
#   * builder  — installs all Python deps + the torenone_kernel package into an
#                isolated venv (kept off the runtime image's apt layer).
#   * runtime  — slim image with only WeasyPrint's native libs + the venv + the
#                service source (torenone_service / torenone_ai are not pip-packaged,
#                so they are provided on PYTHONPATH).
#
# Python 3.11 is the only supported interpreter (pyproject requires-python>=3.11).

# syntax=docker/dockerfile:1

########################  builder  ########################
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Only what's needed to resolve deps and build the kernel package.
# (packages.find points at kernel/src, so kernel + pyproject must be present.)
COPY pyproject.toml ./
COPY kernel ./kernel

RUN python -m venv /opt/venv \
    && pip install --upgrade pip \
    && pip install ".[service,pdf]"

########################  runtime  ########################
FROM python:3.11-slim AS runtime

# WeasyPrint's runtime native dependency is Pango (libpangoft2 covers FreeType text);
# Pillow (a Python dep) handles raster images, so gdk-pixbuf/cairo are not required.
# fonts-dejavu-core gives the PDF a real font; shared-mime-info lets WeasyPrint sniff
# the embedded matplotlib PNGs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        fonts-dejavu-core \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/service/src" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# The venv already contains torenone_kernel + every runtime dependency.
COPY --from=builder /opt/venv /opt/venv
# torenone_service + torenone_ai live in service/src (not pip-packaged) → PYTHONPATH.
COPY service ./service

# Drop privileges — never run the app as root.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness: /health needs no secrets and no external deps (see app.py).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

# Bind all interfaces so the container is reachable; PORT is overridable (Fly/Render).
CMD ["sh", "-c", "uvicorn torenone_service.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
