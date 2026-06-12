# TorenOne — Deployment (engineering service)

> Task 4.6. How to containerise and deploy the FastAPI engineering service
> (`service/src/torenone_service`). The frontend (`web/`) deploys separately (Vercel,
> Phase 6+). **No secret is ever committed** — all secrets are set at deploy time.

## What ships in the image

The `Dockerfile` (repo root) builds a two-stage image:

- **builder** — `pip install ".[service,pdf]"` into an isolated venv. This installs
  the `torenone_kernel` package (the only pip-packaged module — see
  `[tool.setuptools.packages.find]`) plus every runtime dependency, including
  WeasyPrint (the `pdf` extra) so `/design` renders real PDFs.
- **runtime** — `python:3.11-slim` + WeasyPrint's native libs (`libpango-1.0-0`,
  `libpangoft2-1.0-0`, `fonts-dejavu-core`, `shared-mime-info`). `torenone_service`
  and `torenone_ai` are **not** pip-packaged, so they are copied from `service/src`
  and exposed via `PYTHONPATH=/app/service/src`. The app runs as the non-root
  `appuser` and serves `uvicorn torenone_service.main:app` on port **8000**.

`/health` needs no secrets and no external dependencies, so the container boots and
passes its health check even before any secret is set; **protected routes return 503**
until the relevant secret is provided (see below).

## Build & run locally

```bash
# from the repo root
docker build -t torenone-service .

# health only (no secrets needed):
docker run --rm -p 8000:8000 torenone-service
curl -s localhost:8000/health
# {"status":"ok","service":"torenone-engineering-service","version":"0.1.0"}

# full functionality — pass secrets via an env file (NEVER commit it):
docker run --rm -p 8000:8000 --env-file service/.env torenone-service
```

## Required environment / secrets

Documented in `.env.example`. Server-side only — never exposed to the browser.

| Variable | Used by | If unset |
|---|---|---|
| `OPENAI_API_KEY` | `/parse` (AI orchestration) | `/parse` → 503 |
| `OPENAI_MODEL` / `OPENAI_FALLBACK_MODEL` | model selection | defaults `gpt-5.5` / `gpt-5.4-mini` |
| `SUPABASE_JWT_SECRET` | JWT verification (all protected routes) | protected routes → 503 |
| `SUPABASE_JWT_AUD` | JWT audience check | defaults `authenticated` |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase-backed store (Phase 5) | in-memory store for now |

## Deploy to Fly.io

`fly.toml` (repo root) is preconfigured: builds from the `Dockerfile`, `internal_port = 8000`,
HTTPS forced, a `/health` HTTP check, region `jnb` (Johannesburg — closest to Cape Town),
1 GB RAM (headroom for a WeasyPrint + PyNite design run, NFR-5).

```bash
fly launch --no-deploy            # first time only; keeps this fly.toml
fly secrets set \
  OPENAI_API_KEY=... \
  SUPABASE_JWT_SECRET=... \
  SUPABASE_URL=... \
  SUPABASE_SERVICE_ROLE_KEY=...
fly deploy
fly open /health                  # verify liveness
```

`fly secrets set` stores secrets encrypted and injects them as env vars at runtime —
they are never in the image or this repo.

### Alternatives (Render / Railway)

Both auto-detect the `Dockerfile`. Set the same env vars in the dashboard, expose
port 8000, and point the health check at `/health`. No code change required.

## CI verification

The `docker` job in `.github/workflows/ci.yml` builds the image on every push/PR, runs
the container, and asserts `GET /health` returns `200` with the expected JSON. The
deployment **contract** (entrypoint, `PYTHONPATH`, native PDF deps, non-root, Fly health
check) is additionally locked by `service/tests/test_deploy.py` in the Python job.
