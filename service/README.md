# torenone-service (FastAPI)

The engineering service: verifies Supabase JWTs, orchestrates the AI (OpenAI `gpt-5.5` —
parsing & narrative only), runs the **kernel** (all computation), generates the calc-package
PDF, and persists runs/reports to Supabase.

**Status:** the **AI orchestration layer** (Phase 3) lives in `service/src/torenone_ai/`.
The **FastAPI app** (Phase 4) lives in `service/src/torenone_service/` — app skeleton
(health + structured logging) done; auth + `/parse` + `/design` routes in progress.

Run locally:
```bash
uvicorn torenone_service.main:app --reload   # GET /health -> {"status":"ok",...}
```

Hard rules:
- The OpenAI key lives here, never in the browser. It is read from `OPENAI_API_KEY`
  (server-side env only) and is never serialised into any response or log.
- The LLM never computes or invents an engineering number — it only calls kernel tools.
- The kernel (`kernel/`) is imported as a pure package; this service adds HTTP, auth, IO.

## Layout
```
service/
  src/torenone_ai/        # Phase 3 — AI orchestration
    config.py             #   server-side config: API key + model from env, key never exposed
    client.py             #   thin OpenAI client factory (lazy SDK import)
    parsing.py            #   text -> FrameSpec (Structured Outputs, never guesses)
    clarify.py            #   clarifying questions for incomplete/invalid input
    narrative.py          #   report prose; numbers injected from kernel only
  src/torenone_service/   # Phase 4 — FastAPI app
    app.py                #   create_app(): /health (public), /me + /parse + /design (protected)
    auth.py               #   Supabase JWT verification (require_user dependency)
    ai_runtime.py         #   server-side OpenAI client + model (app.state.ai_runtime)
    design_service.py     #   /design kernel dispatch (design/check) + DesignError
    reports.py            #   ReportBuilder (WeasyPrint) + ReportStore (InMemory; Supabase in P5)
    schemas.py            #   HTTP request/response models (Parse*/Design*)
    logging_config.py     #   JSON log formatter + per-request logging
    main.py               #   ASGI entrypoint (uvicorn torenone_service.main:app)
  tests/                  # service tests (run on Python 3.11)
```
