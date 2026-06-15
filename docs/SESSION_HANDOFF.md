# TorenOne — session handoff (2026-06-14)

Full context for continuing work in a new session. Everything below is committed to
`main` and CI-green unless stated otherwise.

---

## ⏩ SESSION 2 CONTINUATION (2026-06-15) — READ THIS FIRST, then `docs/PRODUCTION_READINESS.md`

> A second long session ran on `2026-06-15`. **`main` HEAD = `c99d9ec`**, working tree clean,
> CI green. The **live gap tracker is `docs/PRODUCTION_READINESS.md`** (every item has a
> `[x]`/`[~]`/`[ ]` status + a dated note). The standards-verification audit trail is in
> `docs/SOURCES.md` (see its dated changelog). This block is the bridge.

**Context for the session:** the co-founder (registered structural engineer) is busy writing
master's exams, so the directive is to **complete everything in `PRODUCTION_READINESS.md` that
does NOT depend on him** — i.e. everything except §1 (the validation gate) and the
method/clause/limitations sign-offs. Work proceeds in **batches, P1→P2, committing + pushing
each batch with CI green** (verified via `gh run watch`).

**Standards verification (done this session — all CI-green):** the co-founder supplied the
real PDFs (now in the main-checkout `standards/`, gitignored). Verified clause-by-clause and
fixed real discrepancies — see `SOURCES.md` changelog + commits `6431408`/`3ebf91c`/`5d499c5`/
`7698cd9`:
- **SANS 10162-1** (connections/baseplate): corrected φbr 0.80→0.67, φc 0.65→0.60, anchor φ→0.67,
  bolt stress-area→shank-area + 0.70 thread factor, combined shear+tension elliptical→linear ≤1.4,
  bolt fu 800/1000→830/1040. (Several were ~19% **unconservative**.)
- **SANS 10160-1** (final 2011): ULS factors confirmed; **SLS wind 1.0→0.6** corrected.
- **EN 10025-2:2019**: `fy` verified (all bands matched) → PROVISIONAL→VERIFIED.
- **SANS 10160-2 Table 5** (imposed roof): flat 0.4 was wrong → **area-dependent H2** (0.50→0.25);
  typical frame now 0.25 kN/m².

**KEY DECISION — wind gating (carry forward):** the accurate (lower) imposed load made
gravity-sized members fail the *provisional* ULS-2/3 wind checks. Resolution (user-approved):
**ALL wind-derived checks (ULS-2/3 strength + SLS-2 sway) are now ADVISORY / informational
(non-gating)** — they report utilisations but don't gate `passed`/`governing_utilisation` (new
`CheckResult.informational` flag; excluded from the report's member summary; rendered amber
"ADVISORY"). **When the co-founder validates the wind method → flip ULS wind back to GATING +
flip `design(autosize_for_wind=True)` default on, together.**

**Hardening batches DONE (no engineer needed):**
- **Batch 1** (`dfa6cf0`): docker CI renders a real PDF in the image (3.6); pip-audit + npm-audit
  CI gates (7.2); OpenAI timeout/retries (4.1); 256 KB request body guard (4.4).
- **Batch 2** (`c26aeeb`): slowapi per-IP rate limiting on /parse + /design (4.3); service Sentry,
  init-iff-`SENTRY_DSN` (5.1); web security headers in `next.config.ts` (7.4, CSP deferred).
- **Batch 3** (`5e9249e`+`c99d9ec`): password-reset flow (`/forgot-password` + `/reset-password`)
  + shared 10-char password policy (8.1, 7.3); **owner-only team invites** via a Next server
  action + server-only admin client `web/src/lib/supabase/admin.ts` (8.2); role gating (8.3).
  *(Team-invite arch decision = service-role in a Next server action, server-only — user-chosen.)*

**▶ NEXT: BATCH 4 — deploy/ops (start here).** All in `PRODUCTION_READINESS.md`:
- **3.5** CI/CD deploy-automation workflow (on tag or manual dispatch; activation needs the
  founder's Fly/Vercel tokens as repo secrets — build the workflow + document).
- **6.4** repeatable prod migration runbook (supabase migrations).
- **6.2** report-PDF retention/lifecycle policy for the `reports` Storage bucket.
- **6.3** DB connection-pool sizing under concurrency (session pooler).
- **5.4** minimal product-analytics/event signal (designs run, pass/fail, latency).
Then **Batch 5** (P2 product UI: 9.1 BMD/SFD, 9.2 check-mode toggle, 9.3 audit/provenance panel,
9.4 editable cost) and **Batch 6** (legal drafts: 2.2/2.3/2.4 Terms/Privacy/disclaimer).

**What needs the FOUNDER (not engineer) to *activate* later** (code is built/ready): deploy to
Fly+Vercel+prod-Supabase+domain (§3.1–3.4), OpenAI spend cap (§4.2), Sentry DSN (§5.1) + web
`@sentry/nextjs` + uptime monitor (§5.2), Supabase backup tier (§6.1), prod secret vaults +
rotation (§7.1), CSP per-env (§7.4), buy properly-licensed SABS/BSI standard copies (§2.6),
insurance/lawyer (§2.1/§2.5).

**Run state (this machine):** web on `:3000` and the engineering service on `:8000` are both
running and managed by **Claude Preview** (`.claude/launch.json` — gitignored). The service
entry is a `bash -lc` wrapper that `cd`s to the main checkout, sources `.env`, sets
`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`, and runs the venv uvicorn on `:8000`
(`autoPort:false`). `curl localhost:8000/health` to check.

**Workflow reminders that still hold:** work in the git worktree (`.claude/worktrees/...`);
the engineering service + venv live in the MAIN checkout `/Users/cash/TorenOne`. Local checks:
`PYTHONPATH=kernel/src:service/src:tools /Users/cash/TorenOne/.venv/bin/{pytest,ruff,mypy}` and
always run the **full** `mypy kernel/src service/src`; pin `sqlglot>=27,<28` in the venv. Web:
the worktree `web/` has its own `node_modules` (from `npm ci`); `npm run typecheck|lint|test|build`.
Push to `main` via `git push origin HEAD:main`; watch CI with `gh run watch`. The CI **E2E job
is live** (nightly + manual dispatch, opt-in `RUN_E2E=true`) against a separate Supabase test
project (`pritvkhipuyowjctrpdx`); see `docs/E2E_CI_SETUP.md`.

---

## Where the project stands
- **Phases 1–7: complete.** Kernel (SANS portal-frame design), AI parsing, FastAPI service,
  Supabase (multi-tenant + RLS + auth + storage), full frontend (6.1–6.8), and Phase 7
  integration + Playwright E2E (happy-path / multi-tenant / error-paths) — all done, CI-green.
- **Phase 8: partially done.** 8.5 security pass ✅, 8.4 coverage ✅ (kernel 98%, CI gate at 95%),
  8.6 limitations-mechanism ✅. **8.1/8.2/8.3 + formula review are CO-FOUNDER-gated** (need the
  registered engineer + real past-project data). Validation harness + guide scaffolded (below).
- **Wind actions (user-requested fix): DONE (Parts A + B), PROVISIONAL.** See the dedicated
  section — this is the most important thing for the co-founder to validate.
- `HEAD = 8af09ba` on `main`. Latest CI run: success. Working tree clean.

## The app is LIVE end-to-end locally
- **Web** (Next.js 16) at **http://localhost:3000**, **engineering service** (FastAPI) at
  **http://localhost:8000**, both talking to the **live Supabase project** (`wcjwzpzfoauhixrficzl`).
- Full loop works: sign in → project → describe a frame (NL) → AI parse → review/edit → run
  design → SANS calc-package PDF (stored in Supabase Storage) → run history.

### Running locally (services are NOT auto-started)
Run the engineering service from the MAIN checkout (`/Users/cash/TorenOne`, not the worktree):
```
cd /Users/cash/TorenOne
# one-time: uv venv --python 3.11 .venv && uv pip install -e ".[service,pdf]"
set -a; . ./.env; set +a
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib      # WeasyPrint finds pango/cairo
PYTHONPATH=service/src:kernel/src .venv/bin/uvicorn torenone_service.app:create_app --factory --host 127.0.0.1 --port 8000
```
- The venv at `/Users/cash/TorenOne/.venv` has the deps. Local test commands use
  `PYTHONPATH=kernel/src:service/src:tools` + that venv's pytest/ruff/mypy.
- **Pin sqlglot to the CI version** in the local venv or `supabase/tests` fail spuriously:
  `uv pip install --python /Users/cash/TorenOne/.venv "sqlglot>=27,<28"`.
- Test Supabase user (email confirmation is OFF): `claude-preview-630pm@example.com` /
  `preview-test-12345`. (Its firm differs from some older test projects — use its own projects.)

## Critical gotchas (bit us this session — all fixed, but remember)
1. **Worktree vs main checkout.** Agent works in `.claude/worktrees/...`; the user runs/edits in
   `/Users/cash/TorenOne`. Gitignored files (`.env`, `web/.env.local`) must live in the MAIN
   checkout. Code commits flow to `main`; the running service loads kernel from the main checkout.
2. **CORS + ES256/JWKS auth.** Supabase signs user tokens with **ES256** (asymmetric); the service
   verifies via the project **JWKS** (needs `SUPABASE_URL`), not HS256. CORS middleware allows
   `localhost:3000`. Both already fixed (`98d6db1`, `c12d434`).
3. **Run FULL mypy** (`mypy kernel/src service/src`), not single files — CI caught a re-export
   error I missed (`c57d66f`).
4. **Next 16 renamed `middleware`→`proxy`** (`web/src/proxy.ts`). Read `web/node_modules/next/dist/docs/`
   before writing Next code (per `web/AGENTS.md`).
5. **Never commit secrets**; `.env*` gitignored. `.claude/` gitignored (agent runtime).

## Wind actions — Parts A + B (PROVISIONAL — co-founder must validate)
The user reported wind pressures + combinations were missing from the report. The whole wind chain
(`loads/wind.py` qp, `wind_pressure.py` cpe/cpi, `wind_loads.py` member UDLs, `combinations.py`
ULS-2/3+SLS-2) was built + SANS-cited, but `design.py` never invoked it.
- **Part A (`3041979`):** `design()`/`check()` attach `wind_loads(spec)` to `DesignResult.wind`
  (wind types moved to `models/results.py` to break an import cycle). PDF §11.2 "Characteristic
  Wind Actions" + frontend Wind card show qp, net (cpe−cpi), per-case member loads.
- **Part B (`8af09ba`):** `PortalAnalysis.run_wind_combination()` applies transverse wind to the
  frame; `design()`/`check()` run **ULS-2/3** per wind case, check members, append checks suffixed
  `[ULS-2 wind]`/`[ULS-3 wind]`. **Update (2026-06-15): these wind checks are now ADVISORY
  (informational, non-gating)** — they report utilisations but do NOT fold into
  `passed`/`governing_utilisation` (see the imposed-load note below for why). Mechanically validated
  (`kernel/tests/test_plane_frame_wind.py`).
- **PROVISIONAL:** wind-on-frame **sign conventions + governing case need SANS-worked-example
  validation by the co-founder.** Members are auto-sized on **gravity** and only **CHECKED** (not
  sized) for wind — a wind-governed inadequacy is surfaced honestly, not silently mis-sized.
- **Wind follow-ups — DONE (this session), still PROVISIONAL:**
  - **Auto-size for wind, behind a flag (OFF by default).** `design(spec, autosize_for_wind=True)`
    sizes members for the component-wise envelope of gravity (ULS-1) **and** wind (ULS-2/3), so the
    gating ULS wind checks then pass (≤1.0). **Default stays False** — gravity sizes, wind is only
    CHECKED — until the co-founder validates the method. Flip the default (and optionally expose it
    via the service/API, not yet wired) once validated. Verified on a windy frame: OFF → ULS-wind
    util ~2.5 (fails); ON → ≤1.0 with heavier steel.
  - **SLS-2 wind sway (eaves lateral drift vs Annex D H/400) is now checked** via
    `PortalAnalysis.wind_combination_displacements()` + `_wind_sway_check()`, reported in `design()`
    **and** `check()`. It is **ADVISORY-only (informational, non-gating)**: new
    `CheckResult.informational` flag; `DesignResult.passed`/`governing_utilisation` exclude
    informational checks. Rationale: Annex D is informative, portals often use a relaxed H/150
    practice limit (sign-off needed), and the wind model is PROVISIONAL — so it must not falsely
    fail a design. (The standard 15 m demo frame shows ~45 mm drift = 3.6× H/400; reported as
    ADVISORY in both the PDF and the web Checks table, never red.)
- **ULS-2/3 wind checks are now ADVISORY (2026-06-15).** When the accurate (lower) SANS imposed
  roof load (E2) landed, gravity-sized members started failing the *provisional* ULS wind checks —
  so, consistent with the SLS-sway precedent, the ULS wind checks were made **informational
  (non-gating)** too. So ALL wind-derived checks (ULS-2/3 + SLS-2 sway) are advisory until the
  method is validated.
- **Remaining wind work:** (a) co-founder validates the wind-on-frame method; (b) **once validated,
  flip the ULS-2/3 wind checks back to GATING + flip `autosize_for_wind` default to True** (and
  expose via service/API) — together; (c) revisit the sway limit (H/400 vs H/150) and whether it
  should gate.

## Phase 8 validation harness (ready for the co-founder)
- `kernel/tests/validation/benchmarks.py` — `make_spec(...)` builds a frame from plain numbers;
  `BenchmarkCase` + empty `BENCHMARKS` (gate skips until filled) + a fill-in template.
- `kernel/tests/validation/test_validation.py` — runs each case through the kernel (check + design
  modes), asserts within tolerance. `test_harness_self_check` proves the machinery now.
- `docs/VALIDATION_GUIDE.md` — non-technical, step-by-step walkthrough for reviewing the kernel with
  the (non-techie) structural-engineer co-founder.

## Open threads / next steps (pick up here)
1. **Co-founder validation session (Phase 8.1/8.2 — THE gate):** fill `BENCHMARKS` with a real past
   frame + results; validate the kernel incl. the **wind method** against a worked example.
2. **Wind follow-ups:** auto-size-for-wind (flag, OFF by default) + SLS-2 wind sway (advisory) are
   DONE this session — see the Wind section. Left: co-founder validates → flip the `autosize_for_wind`
   default to True + expose via service/API; revisit the H/400 vs H/150 sway limit.
3. **`SUPABASE_SERVICE_ROLE_KEY`** — the user fixed it in main `.env` (was the anon key). Confirm
   report persistence still works after any service restart.
4. **CI E2E job (`web-e2e`) — DONE / LIVE.** Triggers **manual dispatch + nightly (02:00 UTC)
   only** (never push/PR), runs against a **separate Supabase TEST project** (`pritvkhipuyowjctrpdx`)
   with `RUN_E2E=true` + 7 GitHub secrets set, and a seeded user `e2e@torenone.test`. First full
   run is **green — all 6 specs pass** against the real stack (auth/RLS/`/design`+PDF/Storage/history).
   Enabling it surfaced + fixed a **latent packaging bug**: the report Jinja template wasn't shipped
   in the wheel (`render_pdf` → `TemplateNotFound` → `/design` 502 in the Docker image; fine from
   source). Fixed via `pyproject` `package-data` (`report/*.jinja2`); also raised the Playwright
   per-test timeout to 90 s and made the happy-path wait for navigation. Runbook (incl. how to pause
   it): **`docs/E2E_CI_SETUP.md`**. To pause: `gh variable set RUN_E2E --body false`.
5. **Phase 9** — pilot & YC readiness.

## Doc map
`docs/TASKS.md` (phase-by-phase status, every task annotated), `docs/SOURCES.md` (every transcribed
value + dependency, cited), `docs/VALIDATION_GUIDE.md`, `docs/E2E_CI_SETUP.md` (turn on the CI E2E
job), `standards/README.md` (SANS manifest —
PDFs are local-only / gitignored). Agent memory: `run-engineering-service-locally`,
`supabase-asymmetric-jwt-es256`, `verify-foundation-before-parallel-build`.
