# Enabling the CI E2E job (`web-e2e`)

The Playwright E2E suite (`web/e2e/`) drives the **real** stack: Supabase auth + RLS,
the engineering service (`/design` → kernel + PDF + Storage), and the web app. Only the
non-deterministic OpenAI `/parse` call is mocked. Because it **signs in and writes real
data** (a project, a run, and a fresh "firm B" sign-up *per run*), CI runs it:

- **only on a separate Supabase TEST project** — never production, and
- **only on the nightly schedule (02:00 UTC) and on manual dispatch** — never on push/PR,

and only when the repo variable `RUN_E2E=true` is set. The workflow (`.github/workflows/ci.yml`,
job `web-e2e`) is already wired for this; the steps below turn it on.

## 1. Create the separate Supabase test project

In the Supabase dashboard, create a second project (e.g. `torenone-e2e`). Then from a
checkout with the Supabase CLI:

```bash
supabase link --project-ref <TEST_PROJECT_REF>
supabase db push          # applies supabase/migrations/* (schema, trigger, storage, RLS)
```

`supabase db push` does **not** run `supabase/seed.sql` (that is local-`db reset` only), so
seed the E2E user manually in step 2.

## 2. Seed the E2E user (firm A) — email confirmation OFF

The suite logs in as `E2E_EMAIL` / `E2E_PASSWORD`. In the **test** project:

1. Auth → Providers → Email: turn **"Confirm email" OFF** (so the user can sign in without
   an inbox round-trip).
2. Auth → Users → **Add user** → create e.g. `e2e@torenone.test` with a strong password and
   **Auto Confirm User** checked.

The Task 5.2 sign-up trigger (`handle_new_user`) fires on insert and bootstraps a `firms`
row + `profiles` row automatically (no `firm_id` metadata ⇒ new firm, role `owner`), so no
extra SQL is needed. The "firm B" user is created fresh by the multi-tenant spec at runtime.

## 3. Set the GitHub secrets + variable

All values come from the **test** project (Settings → API, and Settings → Database →
Connection string). `NEXT_PUBLIC_SUPABASE_URL` is the same as `SUPABASE_URL`.

```bash
# From the repo root, authenticated as a repo admin (gh auth login):
gh variable set RUN_E2E --body true

gh secret set SUPABASE_URL                  --body "https://<TEST_PROJECT_REF>.supabase.co"
gh secret set NEXT_PUBLIC_SUPABASE_URL      --body "https://<TEST_PROJECT_REF>.supabase.co"
gh secret set SUPABASE_SERVICE_ROLE_KEY     --body "<test service_role key>"
gh secret set NEXT_PUBLIC_SUPABASE_ANON_KEY --body "<test anon key>"
gh secret set SUPABASE_DB_URL               --body "postgresql://postgres:<pw>@db.<TEST_PROJECT_REF>.supabase.co:5432/postgres"
gh secret set E2E_EMAIL                     --body "e2e@torenone.test"
gh secret set E2E_PASSWORD                  --body "<the password from step 2>"
```

> Secrets are write-only in GitHub and never printed back. Do not paste them into commits,
> issues, or chat. Prefer `gh secret set NAME < file` to avoid shell history if you like.

## 4. Run it and confirm green

```bash
gh workflow run CI            # manual dispatch (workflow_dispatch)
gh run watch --exit-status    # or: gh run list --limit 1
```

The `web-e2e` job builds the service image, runs it with the test-project secrets, installs
the Playwright Chromium browser, and runs `npm run e2e` against the real stack. On failure it
uploads the `playwright-report` artifact for debugging. After this, the suite also runs each
night at 02:00 UTC.

## Notes

- The full suite (smoke + happy-path + multi-tenant + 3 error-paths) passes locally in ~51s
  with the service running and `E2E_EMAIL`/`E2E_PASSWORD` set (Playwright is serial,
  `workers: 1`, because it mutates shared backend state).
- To temporarily disable CI E2E without removing config: `gh variable set RUN_E2E --body false`.
