# torenone-service (FastAPI)

The engineering service: verifies Supabase JWTs, orchestrates the AI (Claude — parsing &
narrative only), runs the **kernel** (all computation), generates the calc-package PDF, and
persists runs/reports to Supabase.

**Status:** placeholder. Implemented in **Phase 4** (see [docs/TASKS.md](../docs/TASKS.md)).

Hard rules:
- The Anthropic key lives here, never in the browser.
- The LLM never computes or invents an engineering number — it only calls kernel tools.
- The kernel (`kernel/`) is imported as a pure package; this service adds HTTP, auth, IO.
