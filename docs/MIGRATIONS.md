# TorenOne — Production migration runbook (§6.4)

> A **repeatable, reviewed** way to apply schema changes to the live Supabase project —
> not ad-hoc SQL in the dashboard. Every migration is a file in `supabase/migrations/`,
> reviewed in a PR, contract-tested in CI, and applied with `supabase db push`.

## Principles

1. **Migrations are code.** Every schema change is a timestamped file under
   `supabase/migrations/` (`YYYYMMDDHHMMSS_name.sql`), committed and reviewed. Never
   edit the production schema by hand in the dashboard — it diverges from the repo and
   the next `db push` fights it.
2. **Forward-only, additive-first.** Prefer additive changes (new tables/columns/
   policies). Destructive changes (drop/rename) ship in their own migration *after* the
   code that stopped using the old shape is deployed.
3. **CI gates the SQL before it ever reaches prod.** `supabase/tests/` parses every
   migration with `sqlglot` and behaviourally applies the whole stack (incl. RLS
   isolation) against a real Postgres in CI. A migration that breaks the contract fails
   the `python` job — it can't merge.
4. **Back up before you push.** PITR / a manual backup must exist before a production
   `db push` (see `docs/DB_OPS.md` / §6.1).

## One-time setup (founder, per machine)

```bash
brew install supabase/tap/supabase          # or see supabase.com/docs/guides/cli
supabase login                              # opens a browser for the access token
supabase link --project-ref <PROD_PROJECT_REF>   # from the project's dashboard URL
```

`supabase link` writes the project ref locally (it does **not** store secrets in the
repo). The DB password is prompted (or `SUPABASE_DB_PASSWORD` in the environment).

## Authoring a migration

```bash
supabase migration new add_something        # creates supabase/migrations/<ts>_add_something.sql
# ... write the SQL ...
```

Then **test locally before opening the PR** — the same gate CI runs:

```bash
# from the repo root, with the pinned test driver
PYTHONPATH=kernel/src:service/src:tools /Users/cash/TorenOne/.venv/bin/pytest supabase/tests -q
```

Open a PR. CI (`python` job) re-runs `supabase/tests` against `postgres:16`, including
the RLS-isolation behavioural test. **Do not merge on red.**

## Applying to production (the repeatable steps)

```bash
# 0. Be on the merged main commit you intend to release.
git switch main && git pull

# 1. Confirm a backup / PITR window exists (docs/DB_OPS.md §6.1).

# 2. DRY RUN — preview exactly what will run against prod. Nothing is applied.
supabase db push --dry-run

# 3. Review the diff. If it matches the migrations you expect, apply:
supabase db push

# 4. Verify.
supabase migration list      # local vs remote applied state should match
```

`supabase db push` applies only migrations not yet recorded in the remote
`supabase_migrations.schema_migrations` table — so it is **idempotent** and safe to
re-run (already-applied migrations are skipped).

## Verifying after a push

- `supabase migration list` — the remote column shows every local migration as applied.
- Smoke the app: a sign-in + a `/design` run that writes a `runs`/`reports` row (RLS
  must still scope it to the caller's firm).
- Watch the service logs / Sentry for any DB errors (`docs/DB_OPS.md`).

## Rollback

There is **no automatic down-migration** (Supabase migrations are forward-only). To
reverse a change:

1. **Preferred:** author a new forward migration that undoes it (e.g. `drop column`),
   review + test + `db push` like any other change. This keeps history linear and
   auditable.
2. **Emergency (data loss):** restore from the PITR backup taken before the push
   (§6.1) — this reverts the *whole* database to that point, so use only for a genuine
   incident, and coordinate (it discards writes since the backup).

Because every migration is reviewed, CI-tested, dry-run-previewed, and idempotent, a
bad migration should be caught well before prod; the new-forward-migration path is the
normal correction.

## Quick reference

| Step | Command |
|---|---|
| New migration | `supabase migration new <name>` |
| Test locally (CI parity) | `pytest supabase/tests -q` |
| Preview against prod | `supabase db push --dry-run` |
| Apply to prod | `supabase db push` |
| Confirm applied | `supabase migration list` |
