# torenone-service (FastAPI)

The engineering service: verifies Supabase JWTs, orchestrates the AI (OpenAI `gpt-5.5` —
parsing & narrative only), runs the **kernel** (all computation), generates the calc-package
PDF, and persists runs/reports to Supabase.

**Status:** the **AI orchestration layer** (Phase 3) lives in `service/src/torenone_ai/`.
The FastAPI app + HTTP routes land in **Phase 4** (see [docs/TASKS.md](../docs/TASKS.md)).

Hard rules:
- The OpenAI key lives here, never in the browser. It is read from `OPENAI_API_KEY`
  (server-side env only) and is never serialised into any response or log.
- The LLM never computes or invents an engineering number — it only calls kernel tools.
- The kernel (`kernel/`) is imported as a pure package; this service adds HTTP, auth, IO.

## Layout
```
service/
  src/torenone_ai/      # Phase 3 — AI orchestration (OpenAI client, parsing, narrative)
    config.py           #   server-side config: API key + model from env, key never exposed
    client.py           #   thin OpenAI client factory (lazy SDK import)
  tests/                # Phase 3+ service tests (run on the default interpreter)
```
