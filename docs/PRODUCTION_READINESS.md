# TorenOne — Production-Readiness Gap Analysis

> **Purpose:** the single working checklist to get the MVP from "works on our machines + CI"
> to "a real Cape Town firm can run a real project and we'd stake our name on it." Grounded
> in the actual codebase as of `main@06d2592` (2026-06-15), not a generic checklist.
>
> **How to use:** work top-down by priority. Tick items as they land. Each item has an
> **owner**, a **why**, and a concrete **done-when**. Update this file in real time.

---

## The one-paragraph truth

The app is **technically functional end-to-end** (auth → AI parse → deterministic SANS
kernel → calc-package PDF → multi-tenant storage → history), CI is green, and the E2E suite
runs nightly against a real stack. **But it is not safe to put in front of a real firm yet**,
for one dominant reason: **the kernel produces structural-engineering numbers that no
registered engineer has validated** (PRD NFR-1, "accuracy is paramount"). ~13 values/methods
are flagged `PROVISIONAL` (`docs/SOURCES.md`). Until a Pr.Eng signs those off against worked
examples + a real past project, the output is *plausible but unverified* — and people build
load-bearing steel from it. Secondary gaps: no live deployment, no legal/liability scaffolding
(critical for this domain), and no production observability/limits.

**Sequencing in one line:** Validation gate → Legal/insurance → Deploy + observability →
Pilot. Do not invite a firm before the first two are done.

---

## Status at a glance

| # | Area | Severity | Owner | State |
|---|------|----------|-------|-------|
| 1 | Engineering validation gate (the moat) | **P0** | Co-founder (Pr.Eng) | ❌ Not started |
| 2 | Legal, liability & compliance | **P0** | Founder + lawyer | ❌ Not started |
| 3 | Live deployment (service + web) | **P0** | Eng | ❌ Not done (configured only) |
| 4 | Reliability & cost controls (OpenAI, rate limits) | **P1** | Eng | ❌ Absent |
| 5 | Observability (errors, uptime, logs) | **P1** | Eng | ❌ Absent |
| 6 | Data durability & ops (backups, retention) | **P1** | Eng | ⚠️ Default only |
| 7 | Security hardening for prod | **P1** | Eng | 🟡 Partial (8.5 done) |
| 8 | Auth/account lifecycle | **P1** | Eng | 🟡 Partial |
| 9 | Product completeness (deferred FRs) | **P2** | Eng + Founder | 🟡 Partial |
| 10 | Pilot readiness & GTM evidence (Phase 9) | **P2** | Founder | ❌ Not started |

Severity: **P0** = blocks the first real customer (life-safety + legal). **P1** = needed
before relying on it / scaling past a hand-held pilot. **P2** = polish / competitive edge.

---

## P0 — Blocks the first real customer

### 1. Engineering validation gate  ·  owner: **co-founder (registered engineer)**
This is the whole ballgame. The tool is a structural engineer; an unvalidated structural
engineer is a liability, not a product.

- [~] **1.1 Validate every `PROVISIONAL` value/method** (`docs/SOURCES.md`). **Progress
  2026-06-15 — SANS 10162-1 verification pass done:** connection coefficients (1.15),
  baseplate φ-factors (1.16), `fy` base (S355JR 355/480 via Table 6), and the cl. 8.7 sway
  formula are now **transcribed + verified clause-by-clause against the official PDF** — which
  *caught and corrected several discrepancies* (bolt bearing φbr 0.80→0.67, baseplate φc
  0.65→0.60, anchor φ 0.80→0.67, bolt area stress→shank +0.70 thread factor, combined
  elliptical→linear ≤1.4, bolt fu 800/1000→830/1040; several were ~19% unconservative).
  **Also 2026-06-15 — SANS 10160-1 (load combos, E9) verified** vs the *final* Ed 1.1 + Amdt 1:
  ULS factors confirmed unchanged (γG 1.2/0.9, STR-P 1.35, imposed 1.6, wind 1.3; ψ
  inaccessible-roof/wind-accompanying = 0); **SLS wind factor corrected 1.0→0.6** (eq. 10).
  **Also 2026-06-15 — `fy` verified** vs **EN 10025-2:2019 Table 6** (all thickness bands match).
  **Also 2026-06-15 — imposed roof load (E2) verified** vs **SANS 10160-2 Table 5**: the flat
  0.4 kN/m² was wrong → replaced with the area-dependent category-H2 value (0.50→0.25). This
  lower load exposed that gravity-sized members fail the *provisional* ULS-2/3 wind checks, so
  those wind checks were made **advisory (non-gating)** like SLS sway, until the wind method is
  validated. **Still open:** section properties (E1) Pr.Eng spot-check, the connection/baseplate
  *methods* (T-stub, bearing model), and the **wind-on-frame method** (validate → then flip wind
  checks to gating + auto-size-for-wind on). *Done-when:* each `SOURCES.md` row is `VERIFIED` with the
  engineer's initials + date (the code↔standard transcription is now done; the Pr.Eng's
  professional sign-off is the remaining half).
- [ ] **1.2 Fill the benchmark validation harness (Phase 8.1/8.2 — THE gate, PRD NFR-1).**
  Put one real past portal frame + its original results into `kernel/tests/validation/`
  (`BENCHMARKS`); the gate currently skips while empty. *Done-when:* the kernel matches the
  engineer's real design (sections + utilisations) within agreed tolerance, **in CI**.
- [ ] **1.3 Worked-example regression suite (Phase 8.3).** Add ≥2 published worked examples as
  permanent `BenchmarkCase`s. *Done-when:* they pass in CI and stay green.
- [ ] **1.4 Formula/clause review (Phase 8.4 review half).** Engineer reads every check's clause
  mapping in the report. *Done-when:* signed off.
- [ ] **1.5 Confirm the limitations list is complete (Phase 8.6).** *Done-when:* engineer
  agrees the "out of scope / engineer-must-verify" block omits nothing dangerous.
- [ ] **1.6 Wind decision.** After 1.1, decide: flip `design(autosize_for_wind=True)` default +
  expose via service/API, and whether SLS-2 sway should gate (currently advisory). See
  `SESSION_HANDOFF.md` Wind section.
- [x] **1.7 Standards PDFs present + verified.** SANS 10162-1:2011, SANS 10160-1:2011 (final),
  SANS 10160-2:2011, SANS 10160-3:2019, SANS 10100-1, and **EN 10025-2:2019** are all in
  `standards/` and verified against. No engineering standard outstanding. *(Note: SANS 10160-2
  and EN 10025-2 are genuine content via re-hosts — buying properly-licensed copies is a
  procurement/legal item, see §2.)*

> ⚠️ **Hard rule:** no real project output leaves the building until 1.1 + 1.2 are done.
> The "Check mode" (FR-24) is the lower-liability wedge — lead pilots with it.

### 2. Legal, liability & compliance  ·  owner: **founder (+ lawyer/insurer)**
A tool that sizes load-bearing members carries real liability. This is not optional for a
South-African structural-engineering SaaS.

- [ ] **2.1 Professional indemnity / product-liability insurance** appropriate to engineering
  software (or a clear contractual model where the firm's Pr.Eng remains the responsible agent).
- [ ] **2.2 Terms of Service** — explicitly: TorenOne is a *computational aid*; the registered
  engineer is the **authoritative responsible agent** (the PRD's framing — currently only a
  checkbox in `review-step.tsx`). Limit liability; define acceptable use.
- [ ] **2.3 Privacy policy + PoPIA compliance** (SA Protection of Personal Information Act) —
  there are **no `terms`/`privacy`/legal routes** in `web/`. Data processing, retention,
  subject rights. (GDPR too if any EU users.)
- [ ] **2.4 In-product liability disclaimer** on the report PDF cover and the results screen
  (beyond the review checkbox) — "computational aid, verified by the deterministic kernel, not a
  substitute for the engineer's professional judgement; engineer must review and stamp."
- [ ] **2.5 Data-processing terms for the AI step** — the user's project description goes to
  OpenAI. Disclose it; confirm it's acceptable to firms; consider a no-train data agreement.
- [ ] **2.6 Properly-licensed copies of the design standards.** The kernel's values are verified
  against the real standards, but two of the source PDFs in `standards/` (**SANS 10160-2** and
  **EN 10025-2:2019**) are genuine content obtained via **re-hosts** (Studocu), and the steelwork
  design guide is a scan. For a commercial product, the firm should hold **purchased SABS/BSI
  licences** for the standards it relies on (copyright exposure — separate from engineering
  correctness). *(SANS 10160-1/-3, SANS 10162-1, SANS 10100-1 are official ISBN copies.)*

### 3. Live deployment  ·  owner: **eng**
Everything below is *configured* (`Dockerfile`, `fly.toml`, `docs/DEPLOY.md`) but **nothing is
actually deployed** — there is no running production service or web app.

- [ ] **3.1 Deploy the engineering service to Fly.io** (`fly deploy`), region `jnb`, with prod
  secrets set (`fly secrets set …`), `/health` passing. *Note:* the recent wheel-packaging bug
  proves the image path was under-tested — keep the E2E job pointed at the deployed image path.
- [ ] **3.2 Deploy the web app to Vercel** with prod env (`NEXT_PUBLIC_*`, service URL). There is
  **no `vercel.json`** yet; wire the project + env + domain.
- [ ] **3.3 Provision the production Supabase project** (separate from the E2E test project):
  `supabase db push` migrations, enable email auth, set a custom SMTP sender, lock down.
- [ ] **3.4 Custom domain + HTTPS** for web and service; set `CORS_ALLOW_ORIGINS` to the real
  origin (not localhost).
- [ ] **3.5 CI/CD deploy automation** — currently deploy is manual. Add a deploy workflow (on
  tag or manual dispatch) so releases are repeatable and auditable.
- [x] **3.6 Harden the `docker` CI job** — done 2026-06-15: a step now runs `design()` +
  `render_pdf()` inside the built image (asserts a real `%PDF`), so packaging regressions like
  the Jinja-template bug fail at build time. (No auth/Supabase needed — pure kernel + WeasyPrint.)

---

## P1 — Needed before relying on it / scaling past a hand-held pilot

### 4. Reliability & cost controls  ·  owner: **eng**
- [x] **4.1 OpenAI hardening** — done 2026-06-15: the client is now built with a 30 s timeout +
  2 bounded retries (both env-overridable: `OPENAI_TIMEOUT_S` / `OPENAI_MAX_RETRIES`), so a
  hung/slow OpenAI call no longer blocks `/parse` indefinitely. (Fallback-model field already
  wired; `max_tokens` cap belongs with 4.2 cost guardrails.)
- [ ] **4.2 OpenAI cost guardrails** — usage/budget cap + alerting; a runaway loop or abuse could
  generate a large bill. Cap tokens per request; monitor spend.
- [x] **4.3 Rate limiting** — done 2026-06-15: `slowapi` per-IP limits on `/parse` + `/design`
  (default 30/min each, env-overridable `PARSE_RATE_LIMIT`/`DESIGN_RATE_LIMIT`) → 429 on abuse.
  Per-app limiter instance (no cross-test state). *(Per-user keying is a possible refinement.)*
- [~] **4.4 Request guards** — done 2026-06-15: a global **max-body-size** middleware (256 KB,
  env `MAX_REQUEST_BYTES`) returns 413 on oversized payloads, on top of the existing 5000-char
  `/parse` cap. *(Remaining: per-request server-side timeout for the CPU-bound `/design` — pairs
  with 4.5 capacity.)*
- [ ] **4.5 Concurrency/capacity** — the service is single-instance and `/design` is CPU-bound
  (FEA + WeasyPrint). Decide min instances / autoscale on Fly; load-test the 60 s NFR under
  a few concurrent designs.

### 5. Observability  ·  owner: **eng**
Currently: structured stdout logs only. No way to know something broke in prod.
- [~] **5.1 Error tracking** — done service-side 2026-06-15: `sentry-sdk` initialised iff
  `SENTRY_DSN` is set (no-op + no key needed for local/dev/tests; `send_default_pii=False`).
  *(Remaining: wire `@sentry/nextjs` into the web app — needs the same DSN.)*
- [ ] **5.2 Uptime/health monitoring + alerting** on `/health` and the web app (paging/email).
- [ ] **5.3 Log aggregation/retention** beyond container stdout (so post-incident debugging is
  possible).
- [ ] **5.4 A minimal product-analytics/event signal** (designs run, pass/fail rate, latency) —
  also feeds the Phase-9 pilot evidence.

### 6. Data durability & ops  ·  owner: **eng**
- [ ] **6.1 Supabase backups** — confirm the production tier's backup/PITR policy; free tier is
  not sufficient for customer data. Document restore steps.
- [ ] **6.2 Report-PDF retention/lifecycle** in the `reports` Storage bucket (they accumulate
  forever today).
- [ ] **6.3 DB connection management** — the service uses the session pooler; verify pool sizing
  under concurrency so designs don't exhaust connections.
- [ ] **6.4 Migration workflow for prod** — a repeatable, reviewed way to apply new migrations to
  the live project (not ad-hoc).

### 7. Security hardening for prod  ·  owner: **eng**  ·  (8.5 security pass already done)
- [ ] **7.1 Secrets management** — production secrets in Fly/Vercel/Supabase vaults, not local
  `.env`. Rotate the keys that have appeared in dev. Confirm `SUPABASE_SERVICE_ROLE_KEY` is the
  real one in prod (open thread #3 in the handoff).
- [x] **7.2 Dependency scanning in CI** — done 2026-06-15: `pip-audit --skip-editable` gates the
  Python job and `npm audit --omit=dev --audit-level=high` gates the web job (dev-only advisories
  excluded per 8.5). Both currently clean (0 vulns).
- [~] **7.3 Auth abuse protections** — done 2026-06-15: client-side **password policy** raised
  to a shared 10-char minimum (`lib/auth/password.ts`, used by sign-up + reset). *(Remaining,
  Supabase-dashboard settings — founder: login rate-limiting/lockout, the authoritative
  server-side password policy, and **email confirmation ON in the production project**.)*
- [~] **7.4 Security headers / CSP** — done 2026-06-15 for the safe set (next.config.ts):
  X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy,
  X-DNS-Prefetch-Control. *(A full CSP is deferred — it needs per-env `connect-src` for the
  Supabase + service URLs and live testing so it doesn't break Next/Supabase inline scripts.)*

### 8. Auth & account lifecycle  ·  owner: **eng**
- [~] **8.1 Password reset + email verification** — done 2026-06-15: `/forgot-password` (sends a
  reset link via `resetPasswordForEmail`) + `/reset-password` (`updateUser`) flow, reusing the
  existing `/auth/confirm` route for the recovery token; "Forgot your password?" link added to
  login. Email verification (confirm route) already existed. *(Remaining: a live end-to-end test
  against prod SMTP — needs the prod Supabase email sender configured.)*
- [x] **8.2 Team invites** — done 2026-06-15: an **owner-only** "Invite a colleague" form on the
  dashboard → `inviteColleague` server action → Supabase Auth admin `inviteUserByEmail` with
  `firm_id` metadata (consumed by the Task 5.2 trigger → invitee joins as `engineer`). Uses a
  **server-only admin client** (`lib/supabase/admin.ts`). *(Activation needs
  `SUPABASE_SERVICE_ROLE_KEY` in the web deployment's server env + the prod Supabase Site URL /
  invite email template — founder.)*
- [x] **8.3 Roles** — done 2026-06-15: role is read server-side; the invite UI + action are
  **gated to `owner`** (engineers can't invite). Sufficient role-gating for the pilot.

---

## P2 — Polish & competitive edge

### 9. Product completeness (deferred FRs)  ·  owner: **eng + founder**
From `docs/TASKS.md` Phase 6.6 (shipped core, these sub-items deferred):
- [ ] **9.1 Interactive on-screen BMD/SFD + stick model** (FR-32) before PDF export — a key
  "show-your-working" trust/demo feature.
- [ ] **9.2 Check-mode toggle in the UI** (FR-24) — the lower-liability wedge; backend exists,
  surface it prominently in the wizard.
- [ ] **9.3 Audit / "show-your-working" panel + deterministic-kernel provenance badge** (FR-26)
  in the web results (it's in the PDF; bring it on-screen).
- [ ] **9.4 Editable cost-per-ton input** (FR-25/31) on the results screen.

### 10. Pilot readiness & GTM (Phase 9)  ·  owner: **founder**
- [ ] **10.1 Final design/QA polish** so the report PDF looks stamp-worthy (Phase 9.1).
- [ ] **10.2 Onboard 3–5 Cape Town firms** on real projects (Phase 9.2) — only after P0 #1+#2.
- [ ] **10.3 Capture pilot evidence** — time saved (days → minutes), ≥1 paying firm,
  testimonials/logos (Phase 9.3).
- [ ] **10.4 Update the YC application + record the founder demo** (Phase 9.4/9.5).

---

## Recommended order of operations

1. **Co-founder validation session (#1)** — start now; nothing real ships without it. Parallelise:
   the engineer validates while eng does deploy/observability.
2. **Legal + insurance (#2)** — long lead time; start in parallel with #1.
3. **Deploy + observability + reliability (#3, #4, #5)** — eng track, in parallel with #1/#2.
4. **Data/security/auth hardening (#6, #7, #8)** — before the pilot opens up.
5. **Product polish + pilot (#9, #10)** — once the above hold.

**Definition of "production-ready" (MVP):** PRD §10 acceptance met — all FRs tested; **validation
gate passed (real project within tolerance)**; full happy path live on real infra; multi-tenant
verified; CI green + kernel ≥95%; legal/insurance in place; observability live; ≥1 real firm has
run a live project.
