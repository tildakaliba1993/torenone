# TorenOne — Go-Live Runbook (the only doc you need)

This is a **complete, step-by-step** guide to take TorenOne from "code-complete + CI-green"
to "live in production." It assumes **no prior context** — follow it top to bottom. Every
command block tells you **which folder to run it in**. Where you click in a dashboard, the
exact menu path is given.

> The **only** thing here that isn't yours to do is the **co-founder's engineering
> validation** (Phase 10). Everything else you can do yourself, now.

---

## 0. How this fits together (read once)

TorenOne is **three deployed pieces** plus GitHub:

| Piece | What it is | Where it runs |
|---|---|---|
| **Web app** | the Next.js site users see (`web/`) | **Netlify** (auto-deploys from GitHub) |
| **Engineering service** | the FastAPI API that runs the SANS kernel + makes the PDF | **Fly.io** (Docker container) |
| **Database / Auth / Storage** | Postgres, login, the report-PDF bucket | **Supabase** (managed) |
| **Code** | the repo | **GitHub** (already connected to Netlify) |

> ❗ The engineering service **cannot** run on Netlify — it's a Python Docker app with
> native PDF libraries and CPU-heavy maths. It goes on **Fly.io**. Netlify hosts only the
> web app. This is normal and expected.

### Folder convention (important)

You'll run commands from two folders. Each block below is labelled. They are:

- 📁 **`/Users/cash/TorenOne`** — the **repo root** (the "main checkout"). Most commands.
- 📁 **`/Users/cash/TorenOne/web`** — the **web app** (only a couple of local web commands).

> Open Terminal. To go to the repo root: `cd /Users/cash/TorenOne` . To go to the web app:
> `cd /Users/cash/TorenOne/web` . The prompt will show where you are.

### What you'll pay for

- **Fly.io**: needs a credit card on file; a small always-warm machine is a few $/month (or near-$0 if it scales to zero — our config does).
- **Supabase**: free tier works to start; **Pro ($25/mo)** is needed for real backups (Phase 7).
- **Netlify**: free tier is fine to launch.
- **OpenAI**: pay-as-you-go for the `/parse` step.
- **SMTP** (sending login/reset emails): a free tier (e.g. Resend) is fine.

### Progress checklist (tick as you go)

- [ ] **Phase 1** — Install tools + accounts
- [ ] **Phase 2** — Production Supabase project
- [ ] **Phase 3** — Deploy the engineering service (Fly.io)
- [ ] **Phase 4** — Deploy the web app (Netlify)
- [ ] **Phase 5** — Connect them (URLs, CORS, email links)
- [ ] **Phase 6** — Custom domain + lock down CORS/CSP
- [ ] **Phase 7** — Backups, retention, observability, cost caps
- [ ] **Phase 8** — Secrets hygiene
- [ ] **Phase 9** — Full production smoke test (go-live acceptance)
- [ ] **Phase 10** — Co-founder validation gate *(the launch blocker — only he can do it)*
- [ ] **Phase 11** — Legal & insurance
- [ ] **Phase 12** — Ongoing: how to ship updates

---

## Phase 1 — Install tools + create accounts

### 1.1 Get the latest code locally

> 📁 **`/Users/cash/TorenOne`**
```bash
cd /Users/cash/TorenOne
git checkout main
git pull origin main
```
This makes sure you have `netlify.toml`, `fly.toml`, the migrations, and everything else.

### 1.2 Install the command-line tools

> 📁 **`/Users/cash/TorenOne`** (location doesn't matter for installs)
```bash
# Homebrew is already installed on this Mac. Install the three CLIs:
brew install flyctl                 # Fly.io
brew install supabase/tap/supabase  # Supabase
brew install gh                     # GitHub (you may already have it)

# Verify:
flyctl version
supabase --version
node --version      # should be v22.x (Netlify uses 22; match locally)
```

### 1.3 Create / confirm accounts

- **GitHub** — ✅ already connected to Netlify.
- **Netlify** — ✅ you have it (site `silver-begonia-0dc433`).
- **Fly.io** — sign up at <https://fly.io/app/sign-up>, then add a credit card (Account → Billing). Then:
  > 📁 **`/Users/cash/TorenOne`**
  ```bash
  fly auth login        # opens a browser to log in
  ```
- **Supabase** — sign up at <https://supabase.com/dashboard>.
- **OpenAI** — you have an API key (it's in your local `.env`). If not: <https://platform.openai.com/api-keys>.
- **Sentry** *(optional, error tracking)* — <https://sentry.io>. You can skip and add later.
- **SMTP provider** *(to send login/reset emails)* — sign up for **Resend** (<https://resend.com>, free tier) or similar. You'll need it in Phase 2.

✅ **Phase 1 done when:** `flyctl version`, `supabase --version`, and `node --version` all print, and `fly auth login` succeeded.

---

## Phase 2 — Production Supabase project

This creates your live database, login system, and report-PDF storage.

### 2.1 Create the project

1. Go to <https://supabase.com/dashboard> and click **New project**.
2. Pick your **Organization** (create one if asked).
3. **Name:** `torenone-prod` (anything you like).
4. **Database Password:** click **Generate a password**, then **COPY IT and save it somewhere safe** (a password manager). You need it for migrations. ⚠️ You cannot see it again later.
5. **Region:** choose the closest to Cape Town — **`West EU (London)` (`eu-west-2`)** is a good default (Supabase has no Africa region).
6. Click **Create new project**. Wait ~2 minutes for it to provision.

### 2.2 Collect the keys you'll need

In the project, click the **gear / Project Settings** (bottom-left), then:

- **Project Settings → API**
  - **Project URL** → this is your `SUPABASE_URL` (looks like `https://abcdwxyz.supabase.co`).
  - **Project API keys → `anon` `public`** → this is `SUPABASE_ANON_KEY` (safe for the browser).
  - **Project API keys → `service_role` `secret`** → this is `SUPABASE_SERVICE_ROLE_KEY`. ⚠️ **Server-side only — never put this in a `NEXT_PUBLIC_` variable.**
- **Project Settings → General**
  - **Reference ID** → this is your `<PROJECT_REF>` (the bit before `.supabase.co`). Save it.
- **Project Settings → Database → Connection string → "Transaction" / "Connection pooling"**
  - Copy the **Transaction pooler** URI (host ends in `...pooler.supabase.com`, **port `6543`**). It looks like:
    `postgresql://postgres.<PROJECT_REF>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:6543/postgres`
  - Replace `[YOUR-PASSWORD]` with the DB password from step 2.1 → this is your `SUPABASE_DB_URL`. (We use the pooler so many small connections share few backends — see `docs/DB_OPS.md`.)

> 📝 **Keep a scratch note** with: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `PROJECT_REF`, `SUPABASE_DB_URL`. You'll paste these into Fly and Netlify.

### 2.3 Apply the database schema (migrations)

This creates the 5 tables, the sign-up trigger, the private `reports` storage bucket, and the row-level-security rules.

> 📁 **`/Users/cash/TorenOne`**
```bash
cd /Users/cash/TorenOne
supabase link --project-ref <PROJECT_REF>      # paste your ref; it will ask for the DB password
supabase db push --dry-run                     # PREVIEW — shows what will run, changes nothing
supabase db push                               # APPLY
supabase migration list                        # CONFIRM — every migration should show as applied
```
(Full detail + rollback notes: `docs/MIGRATIONS.md`.)

### 2.4 Configure Auth (this is where you got stuck before — do it slowly)

All of this is in the Supabase dashboard, left sidebar **Authentication**.

**(a) Turn on email confirmation**
- **Authentication → Sign In / Providers** (older UI: **Providers**) → click **Email**.
- Turn **"Confirm email" ON**. Save. *(Now new users must click a link in their email before they can log in — correct for production.)*

**(b) Set the site URL + redirect URLs** — so confirmation/reset/invite links point at your live site.
- **Authentication → URL Configuration.**
- **Site URL:** `https://silver-begonia-0dc433.netlify.app`
  *(this is your current Netlify URL; if you add a custom domain in Phase 6, change this to that domain).*
- **Redirect URLs → Add URL:** add **both**:
  - `https://silver-begonia-0dc433.netlify.app/**`
  - (later, if you add a custom domain) `https://app.yourdomain.co.za/**`
- Save.

**(c) Set up email sending (SMTP)** — without this, Supabase's built-in email is rate-limited and not for production.
- Get SMTP credentials from your provider. **Resend example:** sign in to Resend → **API Keys** → create one; their SMTP settings are Host `smtp.resend.com`, Port `465`, Username `resend`, Password = your Resend API key. (Any provider works — SendGrid, Postmark, Amazon SES, etc.)
- In Supabase: **Authentication → Emails → SMTP Settings** (older UI: **Project Settings → Auth → SMTP**).
- Toggle **Enable custom SMTP** and fill in:
  - **Sender email:** e.g. `no-reply@yourdomain.co.za` (must be a domain you've verified with the SMTP provider)
  - **Sender name:** `TorenOne`
  - **Host / Port / Username / Password:** from your provider.
- Save, then use the **"Send test email"** button if present to confirm it works.

> If you don't have a domain yet, you can defer custom SMTP and test with the built-in
> email for a *handful* of accounts — but set up SMTP before inviting real firms.

### 2.5 (Storage is already done)

The migration in 2.3 created the private **`reports`** bucket with per-firm access rules. Nothing to click. You can see it under **Storage** in the sidebar.

✅ **Phase 2 done when:** `supabase migration list` shows all migrations applied; Auth has Confirm-email ON, the Site URL + redirect URLs set, and SMTP configured.

---

## Phase 3 — Deploy the engineering service to Fly.io

This puts the FastAPI API (kernel + PDF) online. It builds from the `Dockerfile` + `fly.toml` already in the repo.

### 3.1 Create the Fly app (first time only)

> 📁 **`/Users/cash/TorenOne`**
```bash
cd /Users/cash/TorenOne
fly launch --no-deploy
```
Answer the prompts:
- **"An existing fly.toml was found. Would you like to copy its configuration?"** → **Yes**.
- **App name:** press Enter to try `torenone-engineering-service`. If it says the name is taken, type another (e.g. `torenone-eng-<yourname>`). **Write down the final name** — your service URL will be `https://<that-name>.fly.dev`.
- **Region:** it's preset to `jnb` (Johannesburg) in `fly.toml` — keep it.
- **"Would you like to set up a Postgres / Redis / Tigris database?"** → **No** to all (we use Supabase).
- **"Would you like to deploy now?"** → **No** (we set secrets first).

### 3.2 Set the service secrets

Use the values from your Phase 2 scratch note. Replace each `...` .

> 📁 **`/Users/cash/TorenOne`**
```bash
cd /Users/cash/TorenOne
fly secrets set \
  OPENAI_API_KEY="sk-..." \
  SUPABASE_URL="https://<PROJECT_REF>.supabase.co" \
  SUPABASE_SERVICE_ROLE_KEY="<service_role secret>" \
  SUPABASE_DB_URL="postgresql://postgres.<PROJECT_REF>:<DB_PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres" \
  CORS_ALLOW_ORIGINS="https://silver-begonia-0dc433.netlify.app"
```
Notes:
- `SUPABASE_URL` is used for **two** things: verifying user logins (JWKS) **and** uploading PDFs.
- `CORS_ALLOW_ORIGINS` is your **web** URL (the Netlify one). If you add a custom domain in Phase 6, re-run `fly secrets set CORS_ALLOW_ORIGINS="https://app.yourdomain.co.za,https://silver-begonia-0dc433.netlify.app"`.
- Optional extras you can add the same way: `OPENAI_MAX_OUTPUT_TOKENS="2048"`, `DESIGN_TIMEOUT_S="120"`, `SENTRY_DSN="..."` (Phase 7).

### 3.3 Deploy

> 📁 **`/Users/cash/TorenOne`**
```bash
cd /Users/cash/TorenOne
fly deploy
```
This builds the Docker image and releases it (takes a few minutes the first time).

### 3.4 Verify the service is up

> 📁 **`/Users/cash/TorenOne`**
```bash
curl https://<your-fly-app-name>.fly.dev/health
# expect: {"status":"ok","service":"torenone-engineering-service","version":"0.1.0"}
```
If you get that JSON, the service is live. **Write down your service URL** — Netlify needs it next.

> Troubleshooting: `fly logs` shows live logs. `fly status` shows machine health. If `/health`
> fails, check `fly logs` for a missing-secret or build error.

✅ **Phase 3 done when:** `curl .../health` returns `{"status":"ok",...}`.

---

## Phase 4 — Deploy the web app to Netlify

Your Netlify site (`silver-begonia-0dc433`) is already connected to GitHub but currently shows
"Page not found" because it was building from the repo root. The `netlify.toml` we just added
fixes that (it points the build at `web/`). Now we set the environment variables and redeploy.

### 4.1 Make sure `netlify.toml` is on GitHub

It's committed to `main` (this guide ships with it). Confirm your local main is current:

> 📁 **`/Users/cash/TorenOne`**
```bash
cd /Users/cash/TorenOne
git pull origin main
ls netlify.toml        # should exist
```

### 4.2 Set the web environment variables in Netlify

In the Netlify dashboard for your site:
- Go to **Site configuration → Environment variables → Add a variable → Add a single variable** (do this for each).

Add these (values from your scratch notes):

| Key | Value | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<PROJECT_REF>.supabase.co` | public |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | your `anon public` key | public |
| `NEXT_PUBLIC_ENGINEERING_SERVICE_URL` | `https://<your-fly-app-name>.fly.dev` | the Fly URL from Phase 3 |
| `SUPABASE_SERVICE_ROLE_KEY` | your `service_role secret` key | **mark "Contains secret values"** — needed for owner team-invites |

Optional (add later if/when you set up Sentry — Phase 7): `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_DSN`.

> Leave **`CSP_ENFORCE`** unset for now (we verify the security policy in report-only mode first, Phase 6).

### 4.3 Trigger a deploy

- Go to **Deploys → Trigger deploy → Deploy site** (or just push any commit — Netlify rebuilds automatically).
- Watch the deploy log. It should: detect Next.js, install deps in `web/`, run `npm run build`, and publish. It will take 2–4 minutes.

### 4.4 Verify the web app

- Open `https://silver-begonia-0dc433.netlify.app`.
- You should see the **TorenOne landing page** (not "Page not found").
- Click **Start a design** → it should reach the **sign-up** screen.

> Troubleshooting: if the deploy fails, open the failed deploy → read the log. The most common
> causes are a missing env var or a Node version mismatch (we pin Node 22 in `netlify.toml`).
> If the page loads but login does nothing, re-check the three `NEXT_PUBLIC_*` values and redeploy
> (public vars are baked in at build time, so you must redeploy after changing them).

✅ **Phase 4 done when:** the landing page loads at your Netlify URL and the sign-up screen opens.

---

## Phase 5 — Connect everything (the first real end-to-end test)

By now: Supabase is live, the service is on Fly, the web app is on Netlify. Confirm they talk.

1. **CORS** — already set in Phase 3.2 to your Netlify URL. (If your web URL changes later, update `CORS_ALLOW_ORIGINS` on Fly and redeploy: `fly secrets set CORS_ALLOW_ORIGINS=...`.)
2. **Supabase Site URL / redirect URLs** — already set in Phase 2.4 to your Netlify URL.
3. **Do a real sign-up:**
   - On the live site, click **Start a design** → **sign up** with a real email + a firm name.
   - Check your inbox → click the **confirmation link** (this is the SMTP from Phase 2.4 working).
   - Log in.
4. **Run one design end-to-end** (this exercises web → service → kernel → PDF → Supabase):
   - Create a project → **Describe** a simple frame (e.g. *"15 m span, 5 m eaves, 8° pitch, 6 m bays, 5 bays, roof dead load 0.2 kPa, wind 36 m/s, terrain B"*) → **Parse**.
   - Review the inputs → tick the confirm box → **Run design**.
   - You should get a **Results** screen (checks, BMD/SFD, cost) and be able to **Download the PDF**.

> If parse fails with "couldn't reach the engineering service" → the `NEXT_PUBLIC_ENGINEERING_SERVICE_URL`
> is wrong or CORS is blocking it. If the design runs but the PDF won't download → check the
> Fly service has `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_DB_URL` set (Phase 3.2).

✅ **Phase 5 done when:** you can sign up → confirm email → log in → run a design → download the PDF on the **live** site.

---

## Phase 6 — Custom domain + lock down security

You can launch on the `*.netlify.app` URL, but a custom domain looks professional.

### 6.1 (Optional) Add a custom domain

1. **Netlify → Domain management → Add a domain** → enter e.g. `app.yourdomain.co.za` → follow the DNS instructions (add the CNAME/records at your registrar). Netlify issues HTTPS automatically.
2. After it's live, update **two** places to the new domain:
   - **Supabase → Authentication → URL Configuration:** set Site URL to `https://app.yourdomain.co.za` and add `https://app.yourdomain.co.za/**` to redirect URLs.
   - **Fly CORS:** > 📁 `/Users/cash/TorenOne` → `fly secrets set CORS_ALLOW_ORIGINS="https://app.yourdomain.co.za,https://silver-begonia-0dc433.netlify.app"`

### 6.2 Enforce the Content-Security-Policy

The app already sends a security policy in **report-only** mode (it reports problems but doesn't block anything). Verify it's clean, then enforce it:

1. Open the live site in Chrome → open **DevTools (View → Developer → Developer Tools) → Console**.
2. Click around: sign in, run a design, download a PDF. Watch for red **"Content-Security-Policy"** violation messages.
3. If there are **none** for normal use → enforce it: in **Netlify → Environment variables**, add `CSP_ENFORCE` = `true`, then **Trigger deploy**.
4. If you *do* see violations for legitimate features, leave `CSP_ENFORCE` unset for now and note them — that's a tuning task, not a launch blocker.

✅ **Phase 6 done when:** (optional) the custom domain works with HTTPS, and the CSP is either enforced cleanly or left in report-only with no surprises.

---

## Phase 7 — Backups, retention, observability, cost caps

### 7.1 Database backups (§6.1)

- **Supabase → Project Settings → Database → Backups.** The free tier has limited/no point-in-time recovery. For customer data, upgrade to **Pro ($25/mo)** and confirm **daily backups / PITR** is on. Note where the restore button is.

### 7.2 Report-PDF retention (§6.2)

Old PDFs accumulate forever otherwise. The repo ships a pruner. Test it in dry-run first:

> 📁 **`/Users/cash/TorenOne`**
```bash
cd /Users/cash/TorenOne
set -a; . ./.env; set +a    # or export the three vars manually
SUPABASE_DB_URL="..." SUPABASE_URL="..." SUPABASE_SERVICE_ROLE_KEY="..." \
  .venv/bin/python tools/prune_reports.py --days 365          # DRY RUN (lists only)
# When you're happy with what it lists, add --apply to actually delete:
#   .venv/bin/python tools/prune_reports.py --days 365 --apply
```
Schedule it monthly later (cron or a scheduled task). Detail: `docs/DATA_RETENTION.md`.

### 7.3 Error tracking (Sentry, optional but recommended) (§5.1)

1. Create a project at <https://sentry.io> (pick "Next.js" for the web one; you can make a second "Python" project for the service).
2. Copy the **DSN**.
3. **Web:** Netlify → Environment variables → add `NEXT_PUBLIC_SENTRY_DSN` = the DSN → **Trigger deploy**.
4. **Service:** > 📁 `/Users/cash/TorenOne` → `fly secrets set SENTRY_DSN="<dsn>"`.
   The code is already wired and stays off until the DSN exists. Force a test error to confirm it appears in Sentry.

### 7.4 OpenAI spend cap (§4.2)

- In the **OpenAI dashboard → Settings → Limits**, set a **monthly budget cap + email alert**. (The per-request token cap is already in the code.)

### 7.5 Uptime monitoring (§5.2)

- Sign up for a free monitor (e.g. **UptimeRobot** or **Better Stack**). Add two checks:
  - `https://<your-fly-app-name>.fly.dev/health`
  - `https://silver-begonia-0dc433.netlify.app/`
- Set it to email/SMS you on failure.

✅ **Phase 7 done when:** backups confirmed, the pruner dry-run works, (optional) Sentry receives a test error, an OpenAI budget alert is set, and an uptime monitor is green.

---

## Phase 8 — Secrets hygiene (§7.1)

- All production secrets now live in **Fly** (`fly secrets`), **Netlify** (env vars), and **Supabase** — not in any committed file. Good.
- **Rotate** any key that was used in development and might be exposed: regenerate the **OpenAI key** and re-set it (`fly secrets set OPENAI_API_KEY=...`). If your Supabase service-role key was ever pasted somewhere risky, you can rotate it in Supabase → Project Settings → API.
- Double-check **no `.env` file is committed** (it's git-ignored; confirm with `git status` showing it untracked).

✅ **Phase 8 done when:** dev keys are rotated and no secret sits in the repo.

---

## Phase 9 — Production smoke test (go-live acceptance)

Run the **whole** path on the live stack, as a real user would:

1. **Sign up** with a fresh email → receive + click the **confirmation email** → **log in**.
2. **Create a project** → **describe** a frame → **parse** → **review/confirm** → **run design**.
3. Results render (checks, **BMD/SFD diagrams**, provenance, cost) within ~30 s → **download the PDF** and open it.
4. As the firm **owner**, use **Invite a colleague** (on the dashboard) → the invitee gets an email and can join the firm.
5. **Isolation check:** sign up a **second, different firm** → confirm it **cannot** see the first firm's projects (the URL of the first firm's project should show "Project not found").
6. Glance at **Sentry** (no unexpected errors), the **uptime monitor** (green), and **Fly logs** (`fly logs`, clean).

✅ **Phase 9 done when:** every step above passes on the live site. **Your infrastructure is now production-ready.**

---

## Phase 10 — Co-founder validation gate *(the launch blocker — only he can do it)*

> ⚠️ **Do not invite a real paying firm until this is done.** Everything above can be live as
> an internal/staging environment, but TorenOne produces structural-engineering numbers, and a
> registered engineer must validate them first (PRD NFR-1).

Hand your co-founder **`docs/VALIDATION_GUIDE.md`** and run the session in it. His concrete
deliverables are the **sign-off checklist (Part 5)** in that file (§1.1–1.6). The two that
*block launch* are:
- **1.1** he signs off the provisional methods (incl. the wind method), and
- **1.2** you put one real past frame + its results into the benchmark test (he picks the frame; you type the numbers — no coding).

When he signs off and the benchmark passes in CI, the engineering green light is given.

✅ **Phase 10 done when:** the co-founder has signed §1.1 + §1.2 and the benchmark test is green in CI.

---

## Phase 11 — Legal & insurance (start early — long lead times) (§2)

These don't block deploy, but they **do** block inviting real firms. Start them in parallel:
- **Professional-indemnity / product-liability insurance** appropriate to engineering software (or a written model where the firm's own registered engineer is the responsible agent).
- **Get an attorney to finalise the Terms + Privacy drafts** already in the app at `/terms` and `/privacy` — they contain `[bracketed]` placeholders (legal name, registration no., Information Officer, sub-processors, liability cap) that a lawyer completes. They are clearly marked "Draft — not legal advice."
- **OpenAI data-processing terms** (it's disclosed in the privacy policy; consider a no-training data agreement).
- **Buy properly-licensed copies** of the SANS/EN standards the kernel relies on.

✅ **Phase 11 done when:** insurance is in place and a lawyer has signed off the Terms + Privacy.

---

## Phase 12 — Ongoing: how to ship updates after launch

- **Web change:** merge to `main` → **Netlify rebuilds and publishes automatically**. Nothing else to do.
- **Service change:** > 📁 `/Users/cash/TorenOne` → `fly deploy`. (Or set up the automated workflow: `gh variable set DEPLOY_ENABLED --body true` + `gh secret set FLY_API_TOKEN --body "$(fly tokens create deploy)"`, then deploy by tagging: `git tag v0.1.1 && git push origin v0.1.1`.)
- **Database change:** add a migration and run `supabase db push` (see `docs/MIGRATIONS.md`). Always `--dry-run` first.

---

## You're live when…

(PRD §10 definition of a production-ready MVP)

- ✅ Code complete + CI green + kernel ≥95% coverage *(done)*
- ✅ Full happy path live on real infra **(Phases 2–9)**
- ✅ Multi-tenant isolation verified **(Phase 9, step 5)**
- ⛔ **Validation gate passed — real project within tolerance (Phase 10 — co-founder)**
- ⛔ Legal/insurance in place **(Phase 11)**
- ✅ Observability live **(Phase 7)**
- ⛔ ≥1 real firm has run a live project *(after Phases 10 + 11)*

When Phases 2–11 are all ticked → **invite your first firm and launch.** 🚀

---

### Appendix — companion docs (you don't need to read these to launch)

These are deeper references this runbook already summarises: `DEPLOY.md` (service image internals),
`MIGRATIONS.md` (DB migration detail + rollback), `DB_OPS.md` (connection sizing), `DATA_RETENTION.md`
(the pruner), `VALIDATION_GUIDE.md` (the co-founder session), `PRODUCTION_READINESS.md` (the full
gap tracker). **For launch, this file is enough.**
