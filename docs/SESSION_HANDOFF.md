# TorenOne — session handoff (2026-06-14)

Full context for continuing work in a new session. Everything below is committed to
`main` and CI-green unless stated otherwise.

---

## ⏩⏩ SESSION 3 CONTINUATION (2026-06-24) — **READ THIS FIRST**, then the Session 2 block, then `docs/PRODUCTION_READINESS.md`

> Third long session (2026-06-16 → 2026-06-24). **`main` HEAD = `38d6844`**, branch pushes go
> to `main`, working tree clean, **CI green**. This block is the freshest bridge; the Session 2
> block below it and `docs/PRODUCTION_READINESS.md` (the live gap tracker) remain valid for
> everything earlier. Project: **TorenOne — AI structural engineer for single-bay SANS steel
> portal frames.** The product is **LIVE** (web on Netlify at **torenone.com**, service on Fly).

### What this session did (all on `main`, CI-green)

**A. Finished the production-readiness program — Batches 4–8 (all non-co-founder eng/code work):**
- **Batch 4 (deploy/ops):** `deploy.yml` (Fly service deploy, opt-in), `docs/MIGRATIONS.md`,
  `docs/DATA_RETENTION.md` + `tools/prune_reports.py` (PDF retention pruner), `docs/DB_OPS.md` +
  bounded DB connect, `service/.../analytics.py` (one `event="design_run"` structured log/design).
- **Batch 5 (product UI + a kernel data-exposure change):** new `kernel/.../analysis/diagram_data.py`
  + `DesignResult.diagram` (sampled BMD/SFD/axial for the governing ULS-1; the PDF now renders from
  it — one source of truth). Web: on-screen BMD/SFD + stick model, check-mode framing, "Deterministic
  kernel — not AI" provenance badge + standards card, editable cost-per-tonne.
- **Batch 6 (legal drafts):** `web/src/app/(legal)/terms` + `/privacy` (DRAFTS — attorney must
  finalise) + liability disclaimer on the PDF cover and results screen.
- **Batch 7:** OpenAI per-request output-token cap (`OPENAI_MAX_OUTPUT_TOKENS`), CSP **report-only**
  (`web/src/lib/security/csp.ts`, `CSP_ENFORCE=true` to enforce), `@sentry/nextjs` wired no-op-without-DSN.
- **Batch 8:** `/design` wall-clock timeout (`DESIGN_TIMEOUT_S` → 504). A full re-scan then confirmed
  **no `PRODUCTION_READINESS.md` item has any remaining code component** — see that note below.

**B. Went LIVE + wrote the launch runbook.**
- **DEPLOY DECISION: web → Netlify (NOT Vercel); service → Fly.io; DB → Supabase.** See the
  [[deploy-targets]] memory. `netlify.toml` at repo root (`base="web"`, `NODE_VERSION=22`,
  `@netlify/plugin-nextjs`, **`publish=".next"`** — the publish-dir fix), `vercel.json` removed, the
  `deploy.yml` Vercel job dropped (Netlify **auto-deploys web on every push to `main`**).
- **`docs/GO_LIVE.md` is the single founder runbook** — rewritten, detailed, Netlify-based, Phases 1–12,
  every command labelled with its working directory. **`docs/VALIDATION_GUIDE.md` Part 5** is the
  co-founder's §1.1–1.6 sign-off checklist. The founder has deployed: prod Supabase, Fly service
  (app `torenone-engineering-service`, scale-to-zero → "Suspended" badge is NORMAL), Netlify site
  (`silver-begonia-0dc433` → torenone.com). Full sign-up → confirm → design → PDF worked live.

**C. Major web/UX overhaul (most of the session):**
- **Loading states on EVERY button, consistent** (the shared `Spinner`): form buttons use the Button
  `loading` prop; **`LinkButton`** (Next 16 `useLinkStatus`) shows a spinner during navigation;
  **`SubmitButton`** (`useFormStatus`) for form-action buttons (sign-out). The Run-design button shows
  a live **`KernelProgress`** trace walking the real kernel pipeline (LLM-style).
- **Uniform 120px gutters** across the whole authed app + landing + legal via `APP_GUTTER`
  (`web/src/lib/layout.ts`); per-page `max-w` clamps removed.
- **Unicorn landing page** (`web/src/components/landing/*`): sticky nav with auth buttons, hero with an
  **animated product-preview graphic on the LEFT** (describe → kernel → calc-package), trust bar, stats,
  feature cards, how-it-works, a user-centric **"the moat is the engine"** section that indirectly makes
  the YC **SaaS-Challenger** case, final CTA, footer. Scroll-reveal + float + glow animations (respects
  `prefers-reduced-motion`); all cards share ONE hover effect.
- **Prettier auth** ((auth) layout brand + glow + trust line; Welcome-back login; signup value list).
- **PDF revamp:** the ~22 advisory wind rows collapsed into a compact §5.1 sub-table (caveat stated
  once); geometry diagram de-cluttered; BMD/SFD enlarged with white-boxed, fully-visible peak values.
- **Clickable design runs → on-screen design page** (`/projects/[id]/runs/[runId]`): added the
  `runs.result` jsonb column (full DesignResult persisted by the store) so a past run renders read-only
  via `ResultsStep`.
- **Full projects & designs management** — **real-time CLIENT-SIDE** search / filter / sort / pagination
  (8/page) via `ProjectsManager` + `DesignsManager` (the page loads all rows once, RLS-scoped, and
  filters in memory — instant, no debounce/round-trip). Designs search matches the **displayed** label
  (geometry-derived when unnamed). Rename + delete server actions (`projects/actions.ts`,
  `projects/[id]/actions.ts`) — **delete also removes the report PDFs from Storage** then cascades DB
  rows; row actions wrapped in try/catch (no crashes). Themed `SearchInput`/`FilterSelect`/`Pager`.
  Added the `runs.label` jsonb-adjacent **text** column (editable/searchable).

**D. Bug fixes this session:**
- **Proxy public routes:** `web/src/lib/supabase/proxy.ts` was bouncing `/forgot-password`,
  `/reset-password`, `/terms`, `/privacy` to `/login` — added them to `PUBLIC_PREFIXES`.
- **Forgot-password / email confirm:** `web/src/app/auth/confirm/route.ts` now handles BOTH the PKCE
  `?code=` (Supabase's DEFAULT email format) **and** `token_hash` flows.

### ⚠️ Carry-forward DECISIONS (do not regress)
- **Wind checks stay ADVISORY / non-gating** (ULS-2/3 strength + SLS-2 sway) until the co-founder
  validates the wind method — do NOT re-gate. ([[wind-analysis-provisional]])
- **Deploy = Netlify (web) + Fly (service).** Do NOT reintroduce Vercel. ([[deploy-targets]])
- The legal pages are **DRAFTS** — never represent them as legally sufficient.

### 🔴 PENDING PROD ACTIONS the FOUNDER still owes (not code — they block features live)
1. **Apply the new migrations to prod Supabase** (`supabase db push` from `/Users/cash/TorenOne`):
   `runs.result` (clickable designs) + `runs.label` (designs management). **Until applied, the project
   detail / designs pages read missing columns and break / show empty.** This is the most urgent item.
2. **Forgot-password email delivery:** configure **custom SMTP** + add `https://torenone.com/**` to
   Supabase **Redirect URLs** + Site URL. (Code path is correct; these are dashboard settings —
   `GO_LIVE.md` Phase 2.4.) Also redeploy Fly (`fly deploy`) so the service writes `runs.result` + the
   revamped PDF.
3. Optional founder activations: `CSP_ENFORCE=true`, Sentry DSNs, OpenAI spend cap, uptime monitor,
   backups tier — all in `GO_LIVE.md` Phases 5–7.

### ▶ PROGRAM STATUS / what's left
**Every code/eng item in `PRODUCTION_READINESS.md` is DONE.** Remaining is ONLY: **co-founder
(Pr.Eng)** — §1 validation gate 1.1–1.6 + method/clause/limitations sign-offs + the wind re-gating
decision (`VALIDATION_GUIDE.md`); and **founder accounts/lawyer** — the PENDING PROD ACTIONS above +
finalising legal + insurance + the pilot (§10). **No autonomous coding batches remain** — next code
work will be founder-requested UX/feature polish (this session was largely that). When the user reports
a live bug or asks for a feature, just do it (web auto-deploys on push to `main`).

### How to work (unchanged — see Session 2 block for full detail)
- Work in the **git worktree** (`.claude/worktrees/...`); the engineering service + venv live in the
  **MAIN checkout `/Users/cash/TorenOne`** (the user runs deploy/supabase/fly commands there).
- Local checks: `PYTHONPATH=kernel/src:service/src:tools /Users/cash/TorenOne/.venv/bin/{pytest,ruff,mypy}`;
  ALWAYS run the **full** `mypy kernel/src tools service/src`; pin `sqlglot>=27,<28`. Web: from `web/`,
  `npm run typecheck|lint|test|build` (Node 22). Push to `main` (`git push origin HEAD:main`); watch CI
  with `gh run watch`. Render a PDF to eyeball report changes via the venv (DYLD + worktree PYTHONPATH).
- **Netlify auto-deploys web on push to `main`.** Service deploys are manual (`fly deploy`) or via the
  opt-in `deploy.yml` tag workflow.

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

**Batch 4 — deploy/ops: DONE (2026-06-16, Session 3).** All in `PRODUCTION_READINESS.md`, CI-green:
- **3.5** `.github/workflows/deploy.yml` — Fly (service) + Vercel (web) deploy on `v*` tag / manual
  dispatch (`target` input), `/health` verify; **opt-in/inert** until `DEPLOY_ENABLED=true` +
  `FLY_API_TOKEN`/`VERCEL_*` secrets (founder). Documented in `docs/DEPLOY.md` §CI/CD.
- **6.4** `docs/MIGRATIONS.md` — repeatable prod migration runbook (author → `pytest supabase/tests`
  → `db push --dry-run` → `db push` → verify; forward-only/idempotent + rollback).
- **6.2** `docs/DATA_RETENTION.md` + `tools/prune_reports.py` — 365-day report-PDF retention; an
  idempotent, dry-run-by-default pruner (Storage-then-row), **8 tests**.
- **6.3** `docs/DB_OPS.md` + connect-per-request bounded by `connect_timeout`/`application_name`
  (`SUPABASE_DB_CONNECT_TIMEOUT_S`) + Fly edge concurrency cap (`hard_limit=8`); transaction-pooler
  guidance + pre-pilot load-test checklist.
- **5.4** `service/.../analytics.py` — one structured `event="design_run"` log line per design
  (mode, pass/fail, governing util, tonnage, latency `duration_ms`; no PII), **6 tests**.

**Batch 5 — P2 product UI: DONE (2026-06-16, Session 3).** §9 / `TASKS.md` 6.6 deferred sub-items.
**Not web-only** — 9.1 needed a kernel data-exposure change (user-approved "full Batch 5 incl. kernel
change"). Two commits, CI-green:
- **kernel/service (`9d5facd`):** `DesignResult.diagram` (FrameDiagram/MemberDiagram/DiagramStation)
  — sampled BMD/SFD/axial + node coords for the governing ULS-1 combo, via new
  `analysis/diagram_data.py` (PyNite-only, no matplotlib); populated by `design()`+`check()`. The PDF
  `bmd_sfd_png` now renders from this same data (one source of truth; removed the duplicated PyNite
  build). +12 kernel tests.
- **web:** `frame-diagrams.tsx` BMD/SFD + stick model on results (9.1); check-mode lower-liability
  framing in the wizard (9.2); "Deterministic kernel — not AI" badge + "Provenance & standards" card
  (9.3); editable cost-per-tonne re-costing client-side (9.4). Web 82 tests / typecheck / lint / build
  green.

**Batch 6 — legal drafts: DONE (2026-06-17, Session 3).** `PRODUCTION_READINESS.md` §2, CI-green:
- **2.2** `web/src/app/(legal)/terms` — ToS draft (computational aid; ECSA engineer = authoritative
  responsible agent; warranties/liability/indemnity/SA law). **Marked DRAFT, pending attorney review.**
- **2.3** `web/src/app/(legal)/privacy` — Privacy + PoPIA draft (AI/OpenAI disclosure, trans-border,
  data-subject rights + Information Regulator). **DRAFT, pending attorney review.**
- **2.4** liability box on the **report PDF cover** (kernel template) + `LiabilityNotice` on the
  **results screen**; Terms/Privacy links on landing + a signup agreement line.
Shared `(legal)/layout.tsx` shows a prominent "Draft — not legal advice" banner; `components/legal/prose.tsx`
primitives. Web 86 tests + kernel report disclaimer test; full suite 838 passed.

**Batch 7 — final code slivers: DONE (2026-06-17, Session 3).** The last code-only pieces inside
`[~]` items, none co-founder-dependent (CI-green):
- **4.2 (code half)** per-request OpenAI **output-token cap** (`OPENAI_MAX_OUTPUT_TOKENS`, default 2048;
  `service/.../parsing.py`); spend *monitoring* stays the founder's OpenAI dashboard.
- **7.4** **CSP** shipped **report-only** (`web/src/lib/security/csp.ts`, env-derived connect-src;
  `CSP_ENFORCE=true` to enforce after a verification pass). 5 tests.
- **5.1 (web half)** `@sentry/nextjs` wired (`instrumentation*.ts` + `global-error.tsx`), no-op without
  a DSN; prod npm-audit clean. 5.1 now code-complete (service + web).
`.env.example` documents the new knobs.

**Batch 8 — final guards (2026-06-17, commit `1b05002`):** `/design` per-request wall-clock timeout
(4.4 → done, `DESIGN_TIMEOUT_S`, 504 on exceed). After this a fresh re-scan of
`PRODUCTION_READINESS.md` confirms **no open item has any remaining code component.**

**DEPLOY-TARGET DECISION (2026-06-17): web → Netlify, NOT Vercel** (founder's choice; the Netlify
site `silver-begonia-0dc433` is already connected to GitHub). Code switched accordingly: `vercel.json`
removed → `netlify.toml` added (base `web`, Node 22, `@netlify/plugin-nextjs`); `deploy.yml` Vercel
job removed (Netlify auto-deploys web on push to `main`; the workflow now only deploys the Fly
service). The engineering service stays on **Fly.io** (it can't run on Netlify). **`docs/GO_LIVE.md`
was fully rewritten** into a detailed, self-contained, Netlify-based step-by-step launch runbook
(Phases 1–12, with the working directory marked on every command) — it is the single doc the founder
follows to go live.

**▶ PROGRAM STATUS:** every `PRODUCTION_READINESS.md` item that is **code/eng work** is now **DONE**
(Batches 1–8). What remains is only: **co-founder (Pr.Eng)-gated** — §1 validation gate 1.1–1.6 +
method/clause/limitations sign-offs + the wind re-gating decision; and **founder-account/credential/
money/lawyer-gated** (NOT co-founder) — deploy §3.1–3.4, OpenAI spend cap/alerting (4.2 dashboard),
load-test 4.5, uptime 5.2, log aggregation 5.3, Supabase backups 6.1, prod secret vaults 7.1, Supabase
auth toggles 7.3, prod-SMTP test 8.1, insurance 2.1, OpenAI data agreement 2.5, licensed standards 2.6,
finalising the 2.2/2.3 legal drafts with a lawyer, pilot §10. **No autonomous coding work remains.**

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
- **`docs/GO_LIVE.md`** — the founder's end-to-end **production launch runbook** (Phases A–I:
  prod Supabase → Fly → Vercel → domain/CSP → observability → backups/retention → secrets →
  CI/CD → smoke test), with the exact env per surface. **Start here for the launch.**
- **`docs/VALIDATION_GUIDE.md`** — non-technical co-founder session + the **§1.1–1.6 sign-off
  checklist** (Part 5) — the engineering launch gate.
- Ops mechanics: `docs/DEPLOY.md` (service image/Fly + CI/CD), `docs/MIGRATIONS.md` (prod DB),
  `docs/DB_OPS.md` (pooler/sizing), `docs/DATA_RETENTION.md` (PDF pruning), `docs/E2E_CI_SETUP.md`
  (turn on/pause the CI E2E job).
- Status/provenance: `docs/PRODUCTION_READINESS.md` (the live gap tracker), `docs/TASKS.md`
  (phase-by-phase), `docs/SOURCES.md` (every transcribed value, cited), `standards/README.md`
  (SANS manifest — PDFs local-only / gitignored).
- Agent memory: `production-readiness-batches`, `run-engineering-service-locally`,
  `supabase-asymmetric-jwt-es256`, `verify-foundation-before-parallel-build`.
