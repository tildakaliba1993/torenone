# TorenOne — Project Setup & Isolation

> **Hard requirement: TorenOne is fully self-contained.** It must NOT share any Supabase project,
> Vercel project, GitHub repo, database, storage bucket, or environment with your other work.
> This page is the checklist that keeps it isolated.

## Why isolation matters here
- **Data safety:** TorenOne stores firms' engineering data under multi-tenant RLS. It must never sit
  in a database shared with unrelated projects.
- **Blast radius:** a mistake in another project can never affect TorenOne (and vice-versa).
- **Clean billing/ownership** and a tidy story for YC ("this is its own product, its own infra").

## What is already isolated (done in Phase 0)
- ✅ **Dedicated git repository** — a fresh `git init` at the project root, **no remote yet**, so it is
  not connected to any existing GitHub repo.
- ✅ **Self-contained code** — its own `web/` (own `package.json`, own `node_modules`), its own Python
  `kernel/`/`service/`, its own CI. Nothing is installed globally; nothing references another project.
- ✅ **Own env template** — `.env.example`; real `.env` files are git-ignored.

## What YOU must create — NEW, dedicated resources only
Do **not** reuse anything from your existing projects.

### 1. GitHub — a brand-new repository
- [ ] Create a **new** private repo, e.g. `torenone` (do not push into an existing repo).
- [ ] Add it as the remote and push:
  ```bash
  git remote add origin git@github.com:<you>/torenone.git
  git branch -M main
  git push -u origin main
  ```
- [ ] Confirm `git remote -v` shows **only** the TorenOne repo.

### 2. Supabase — a brand-new project
- [ ] In Supabase, **create a new project** named `torenone` (its own org/project — not an existing one).
- [ ] Use **its own** database, **its own** storage bucket, **its own** API keys.
- [ ] Put its URL + keys in **this project's** `.env` only (never paste another project's keys here, and
      never paste these keys into another project).
- [ ] When we add the schema (Phase 5), migrations live in **this** repo and run against **this** project.

### 3. Vercel — a brand-new project
- [ ] In Vercel, **create a new project** and link it to the **new** GitHub repo above.
- [ ] Set **Root Directory = `web`** (the Next.js app lives in `web/`).
- [ ] Add TorenOne's `NEXT_PUBLIC_*` env vars to **this Vercel project only**.
- [ ] Do **not** `vercel link` this folder to any existing Vercel project.

### 4. Anthropic
- [ ] Use a key scoped/labelled for TorenOne; it lives **only** in the engineering service env
      (`service/`), never in `web/` or the browser.

## Isolation invariants (keep true forever)
- One repo, one Supabase project, one Vercel project — all named for TorenOne, all dedicated.
- No TorenOne secret is ever placed in another project's env, and no other project's secret is placed here.
- The browser only ever receives the Supabase **anon** key and `NEXT_PUBLIC_*` values — never service-role
  keys or the Anthropic key.

## Quick verification
```bash
git remote -v            # shows only the torenone repo (or nothing yet)
grep -R "supabase" .env  # only TorenOne's project URL/keys
```
