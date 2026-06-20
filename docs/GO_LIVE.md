# TorenOne — Go-Live Runbook (founder checklist)

> **Purpose:** one sequenced checklist to take TorenOne from "feature-complete + CI-green"
> to "running in production." Every **code/eng** item is already done (`PRODUCTION_READINESS.md`
> Batches 1–7); what remains needs **accounts, money, dashboard toggles, or a lawyer** — i.e.
> *you* (founder), plus the **one** thing only the **co-founder (Pr.Eng)** can give: the
> validation sign-off.
>
> **Mechanics live in companion docs** — this file sequences them and lists the exact env per
> surface. Deep dives: `DEPLOY.md` (service image/Fly), `MIGRATIONS.md` (DB), `DB_OPS.md`
> (pooler/sizing), `DATA_RETENTION.md` (PDF pruning), `E2E_CI_SETUP.md` (test job),
> `VALIDATION_GUIDE.md` (the co-founder session).

---

## The hard gate (read first)

> ⚠️ **No real customer project ships until the co-founder completes the validation gate
> (`PRODUCTION_READINESS.md` §1.1–1.2).** You can — and should — do **all** of the deploy/infra
> below *in parallel* while he's unavailable, so the moment he signs off you flip to "open."
> Until then, treat any deployment as **internal/staging** and do not invite a real firm.

**Two independent tracks, run them in parallel:**
- **Track A (you, now):** Phases A–I below — stand up live, observable, secured infra.
- **Track B (co-founder, when free):** the validation session — see `VALIDATION_GUIDE.md`.

---

## Phase A — Production Supabase project  ·  (§3.3, 6.1, 7.3)

1. Create a **new** Supabase project (separate from the E2E test project `pritvkhipuyowjctrpdx`). Region close to users.
2. Apply the schema (see `MIGRATIONS.md` for the full runbook):
   ```bash
   supabase link --project-ref <PROD_REF>
   supabase db push --dry-run     # review
   supabase db push
   supabase migration list        # confirm all applied
   ```
3. **Auth settings (dashboard → Authentication):**
   - Turn **Confirm email ON** (§7.3).
   - Set the **Site URL** to your production web origin + add it to **Redirect URLs** (needed for confirm/reset/invite links — §8.1/8.2).
   - Configure a **custom SMTP sender** (§3.3) so password-reset + invite emails actually send.
   - Enable login **rate-limiting / lockout** if available (§7.3).
4. **Backups (§6.1):** confirm the tier has **PITR / daily backups** (free tier is not enough for customer data). Note the restore steps.
5. Capture these values for later phases:
   - `SUPABASE_URL` = `https://<PROD_REF>.supabase.co`
   - `SUPABASE_SERVICE_ROLE_KEY` (Settings → API) — **server-side only, never `NEXT_PUBLIC`**
   - `SUPABASE_ANON_KEY` (public)
   - `SUPABASE_DB_URL` = the **transaction pooler** connection string (**port 6543**, see `DB_OPS.md`)

**Acceptance:** `supabase migration list` shows every migration applied; a test sign-up creates a firm + profile (the 5.2 trigger) and sends a confirmation email.

---

## Phase B — Deploy the engineering service to Fly.io  ·  (§3.1)

Mechanics: `DEPLOY.md`. The repo root has `Dockerfile` + `fly.toml` (region `jnb`).

```bash
fly launch --no-deploy           # first time; keep the existing fly.toml
fly secrets set \
  OPENAI_API_KEY=...             \
  SUPABASE_URL=https://<PROD_REF>.supabase.co  \  # JWKS auth (ES256) + Storage REST
  SUPABASE_SERVICE_ROLE_KEY=...  \
  SUPABASE_DB_URL=...            \  # transaction pooler, :6543
  CORS_ALLOW_ORIGINS=https://app.yourdomain.co.za   # the real web origin (Phase D)
fly deploy
fly open /health                 # expect {"status":"ok",...}
```

**Service env reference**

| Variable | Required? | Notes |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | `/parse` |
| `SUPABASE_URL` | ✅ | JWKS token verification (ES256) **and** Storage REST upload |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | report storage; server-side only |
| `SUPABASE_DB_URL` | ✅ | `runs`/`reports` rows — **transaction pooler :6543** (`DB_OPS.md`) |
| `CORS_ALLOW_ORIGINS` | ✅ | comma-sep; the real web origin(s), not localhost |
| `SENTRY_DSN` (+`SENTRY_ENVIRONMENT`,`SENTRY_TRACES_SAMPLE_RATE`) | ⬚ | error tracking (Phase E) |
| `OPENAI_MAX_OUTPUT_TOKENS` | ⬚ | per-request cost cap (default 2048) |
| `PARSE_RATE_LIMIT` / `DESIGN_RATE_LIMIT` | ⬚ | default `30/minute` each |
| `DESIGN_TIMEOUT_S` | ⬚ | per-request `/design` budget → 504 (default 120 s) |
| `SUPABASE_JWT_AUD` | ⬚ | default `authenticated` |
| `SUPABASE_JWT_SECRET` | ⬚ | HS256 legacy only; not needed with JWKS |

**Acceptance:** `/health` 200 from the Fly URL; `fly logs` shows `service_startup`.

---

## Phase C — Deploy the web app to Vercel  ·  (§3.2)

Import the repo into Vercel (root = `web/`; `web/vercel.json` already pins framework `nextjs` +
region `fra1` — change the region if you prefer). Set env (Project → Settings → Environment Variables):

| Variable | Scope | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | public | prod project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | public | anon key |
| `NEXT_PUBLIC_ENGINEERING_SERVICE_URL` | public | the Fly service URL (Phase B) |
| `SUPABASE_SERVICE_ROLE_KEY` | **server only** | required for **owner team invites** (§8.2 admin client) |
| `NEXT_PUBLIC_SENTRY_DSN` | public | web error tracking (Phase E) |
| `CSP_ENFORCE` | server | leave unset at first (report-only); set `true` after Phase D verification |

Deploy. **Acceptance:** the site loads; sign-in reaches Supabase; a design run hits the Fly service and returns a PDF.

---

## Phase D — Domain, HTTPS, CORS, CSP  ·  (§3.4, 7.4)

1. Point your custom domain at Vercel (web) and, optionally, a subdomain at Fly (service); both enforce HTTPS.
2. Set the service `CORS_ALLOW_ORIGINS` (Phase B) to the **real** web origin and redeploy.
3. Update the Supabase **Site URL / Redirect URLs** (Phase A) to the real domain.
4. **CSP verification (§7.4):** the CSP ships **report-only** by default. Browse the app (sign-in, design run, PDF download) with DevTools open; confirm **no legitimate request is reported blocked**. Then set `CSP_ENFORCE=true` in Vercel and redeploy to enforce it.

**Acceptance:** app fully works on the custom domain over HTTPS; no CORS errors; CSP enforced with no breakage.

---

## Phase E — Observability & cost controls  ·  (§5.1, 5.2, 5.3, 4.2)

1. **Sentry (§5.1)** — create a Sentry project; set `SENTRY_DSN` on Fly and `NEXT_PUBLIC_SENTRY_DSN` (+ optional server `SENTRY_DSN`) on Vercel. The code is already wired and is a no-op until the DSN is set. Trigger a test error; confirm it appears.
2. **OpenAI spend cap (§4.2)** — in the OpenAI dashboard set a **monthly budget cap + alert**. (The per-request token cap is already in code.)
3. **Uptime monitor (§5.2)** — point a checker (e.g. Better Stack / UptimeRobot) at the service `/health` and the web root; alert by email/SMS.
4. **Log retention (§5.3)** — optionally ship Fly/Vercel stdout (already structured JSON) to a log store for post-incident debugging.

**Acceptance:** a forced error shows in Sentry; uptime monitor is green; OpenAI budget alert configured.

---

## Phase F — Data durability & ops  ·  (§6.1, 6.2)

1. **Backups (§6.1)** — confirmed in Phase A; document the restore procedure.
2. **Report-PDF retention (§6.2)** — schedule the pruner monthly (see `DATA_RETENTION.md`). Run it **`--dry-run` for one cycle**, eyeball the output, then enable `--apply`:
   ```bash
   SUPABASE_DB_URL=... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
     python tools/prune_reports.py --days 365   # add --apply when satisfied
   ```

**Acceptance:** a backup/restore path is documented; the retention job is scheduled (dry-run verified).

---

## Phase G — Secrets hygiene  ·  (§7.1)

- All production secrets live in **Fly / Vercel / Supabase vaults** — never in the repo or local `.env`.
- **Rotate** any key that has appeared in dev (OpenAI key, Supabase service-role key).
- Confirm `SUPABASE_SERVICE_ROLE_KEY` in prod is the **real service-role key** (not the anon key — this bit us in dev).

**Acceptance:** no secret in git history is still live; prod uses fresh, vaulted keys.

---

## Phase H — Turn on CI/CD deploy automation  ·  (§3.5)

The `deploy.yml` workflow is built and inert. To activate (see `DEPLOY.md` §CI/CD):
```bash
gh variable set DEPLOY_ENABLED --body true
gh secret set FLY_API_TOKEN --body "$(fly tokens create deploy)"
gh secret set VERCEL_TOKEN --body ...
gh secret set VERCEL_ORG_ID --body ...
gh secret set VERCEL_PROJECT_ID --body ...
# then release:
git tag v0.1.0 && git push origin v0.1.0
```

**Acceptance:** tagging `v*` deploys service + web and the workflow's `/health` check passes.

---

## Phase I — Production smoke test (go-live acceptance)

Run the full happy path against the live stack:
1. Sign up → receive + click the confirmation email → sign in.
2. Create a project → describe a frame → parse → review/confirm → run design.
3. Results render (incl. BMD/SFD, provenance, cost) within the 60 s NFR; download the PDF (signed URL).
4. As an **owner**, invite a colleague → they receive the invite and join the firm.
5. Run a **second firm** and confirm it **cannot** see the first firm's projects (RLS).
6. (Optional) Point the CI `web-e2e` job at this stack and run it (`E2E_CI_SETUP.md`).

**Acceptance:** every step passes; Sentry/uptime quiet; logs clean.

---

## Track B — Co-founder validation gate  ·  (§1)  ·  **the launch blocker**

Only the registered engineer can give this. Run the session in `VALIDATION_GUIDE.md`; his deliverables are the **Sign-off checklist** at the end of that file (§1.1–1.6). **Do not open the pilot until 1.1 + 1.2 are done.**

---

## Legal & commercial (long lead — start early, in parallel)  ·  (§2)

- **2.1** Professional-indemnity / product-liability insurance (or the contractual model where the firm's Pr.Eng is the responsible agent).
- **2.2 / 2.3** Have a **qualified SA attorney finalise** the Terms + Privacy/PoPIA **drafts** at `/terms` and `/privacy` (fill the `[bracketed]` placeholders: legal name, reg no., Information Officer, sub-processors, liability cap, dispute mechanism).
- **2.5** OpenAI data-processing terms (disclose + ideally a no-train agreement).
- **2.6** Buy properly-licensed SABS/BSI copies of the standards the kernel relies on.

---

## Definition of "production-ready MVP" (PRD §10)

All FRs tested ✅ · **validation gate passed (real project within tolerance)** ⛔ co-founder ·
full happy path live on real infra (Phases A–I) · multi-tenant verified ✅ · CI green + kernel ≥95% ✅ ·
legal/insurance in place (§2) · observability live (Phase E) · **≥1 real firm has run a live project**.

When the co-founder signs off §1 and Phases A–I + §2 are done → **you launch.**
