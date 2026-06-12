-- TorenOne initial schema (Phase 5, Task 5.1) — Design §A.7.
--
-- Multi-tenant data model: a `firm` is the tenant root; every other row belongs to
-- exactly one firm. `firm_id` is carried (denormalised) on `runs` and `reports` as
-- well, so the Row-Level Security policies added in Task 5.4 are simple, index-backed
-- equality checks against the caller's `profiles.firm_id` — no recursive joins.
--
-- This migration creates tables + relationships + indexes only. RLS is enabled with
-- its policies in Task 5.4; the auth-driven profile/firm bootstrap is Task 5.2; the
-- Storage bucket for PDFs is Task 5.3.

-- ---------------------------------------------------------------------------
-- firms — the tenant root
-- ---------------------------------------------------------------------------
create table public.firms (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- profiles — links a Supabase auth user to a firm (id == auth.users.id)
-- ---------------------------------------------------------------------------
create table public.profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    firm_id     uuid not null references public.firms (id) on delete restrict,
    name        text,
    role        text not null default 'engineer',
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- projects — owned by a firm
-- ---------------------------------------------------------------------------
create table public.projects (
    id          uuid primary key default gen_random_uuid(),
    firm_id     uuid not null references public.firms (id) on delete cascade,
    name        text not null,
    created_by  uuid not null references public.profiles (id) on delete set null,
    created_at  timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- runs — one design run (the confirmed FrameSpec + kernel outcome summary)
-- ---------------------------------------------------------------------------
create table public.runs (
    id                     uuid primary key default gen_random_uuid(),
    project_id             uuid not null references public.projects (id) on delete cascade,
    firm_id                uuid not null references public.firms (id) on delete cascade,
    frame_spec             jsonb not null,
    mode                   text not null default 'design',
    status                 text not null default 'pending',
    rules_version          jsonb,
    passed                 boolean,
    governing_utilisation  numeric,
    created_by             uuid references public.profiles (id) on delete set null,
    created_at             timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- reports — the generated calc-package PDF (stored in Supabase Storage)
-- ---------------------------------------------------------------------------
create table public.reports (
    id            uuid primary key default gen_random_uuid(),
    run_id        uuid not null references public.runs (id) on delete cascade,
    firm_id       uuid not null references public.firms (id) on delete cascade,
    storage_path  text not null,
    created_at    timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Indexes — every foreign key is indexed (RLS filters + join performance)
-- ---------------------------------------------------------------------------
create index profiles_firm_id_idx on public.profiles (firm_id);
create index projects_firm_id_idx on public.projects (firm_id);
create index projects_created_by_idx on public.projects (created_by);
create index runs_project_id_idx on public.runs (project_id);
create index runs_firm_id_idx on public.runs (firm_id);
create index runs_created_by_idx on public.runs (created_by);
create index reports_run_id_idx on public.reports (run_id);
create index reports_firm_id_idx on public.reports (firm_id);
