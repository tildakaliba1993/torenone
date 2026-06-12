-- TorenOne Row-Level Security (Phase 5, Task 5.4) — Design §A.7 / PRD FR-23.
--
-- Every table is filtered by the caller's firm via public.current_firm_id() (defined
-- in the 5.3 migration: a SECURITY DEFINER lookup of profiles.firm_id for auth.uid()).
-- RLS is ENABLED on all five tables, so with no matching policy the default is DENY.
--
-- Tenant writes that would create or move a row into another firm are blocked by the
-- WITH CHECK clauses; cross-firm reads return zero rows via the USING clauses. firms
-- are created only by the SECURITY DEFINER sign-up trigger (Task 5.2), so users get a
-- read-only policy on their own firm and no insert/update/delete policy at all.

-- ---------------------------------------------------------------------------
-- Enable RLS (default-deny until a policy grants access)
-- ---------------------------------------------------------------------------
alter table public.firms    enable row level security;
alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.runs     enable row level security;
alter table public.reports  enable row level security;

-- ---------------------------------------------------------------------------
-- firms — members may read their own firm (created via the sign-up trigger only)
-- ---------------------------------------------------------------------------
create policy "firms: members read their firm"
on public.firms for select to authenticated
using (id = public.current_firm_id());

-- ---------------------------------------------------------------------------
-- profiles — see firm colleagues; update only your own profile row
-- ---------------------------------------------------------------------------
create policy "profiles: read firm colleagues"
on public.profiles for select to authenticated
using (firm_id = public.current_firm_id());

create policy "profiles: update own profile"
on public.profiles for update to authenticated
using (id = (select auth.uid()))
with check (id = (select auth.uid()) and firm_id = public.current_firm_id());

-- ---------------------------------------------------------------------------
-- projects — full CRUD within the caller's firm
-- ---------------------------------------------------------------------------
create policy "projects: read own firm"
on public.projects for select to authenticated
using (firm_id = public.current_firm_id());

create policy "projects: insert into own firm"
on public.projects for insert to authenticated
with check (firm_id = public.current_firm_id());

create policy "projects: update own firm"
on public.projects for update to authenticated
using (firm_id = public.current_firm_id())
with check (firm_id = public.current_firm_id());

create policy "projects: delete own firm"
on public.projects for delete to authenticated
using (firm_id = public.current_firm_id());

-- ---------------------------------------------------------------------------
-- runs — full CRUD within the caller's firm
-- ---------------------------------------------------------------------------
create policy "runs: read own firm"
on public.runs for select to authenticated
using (firm_id = public.current_firm_id());

create policy "runs: insert into own firm"
on public.runs for insert to authenticated
with check (firm_id = public.current_firm_id());

create policy "runs: update own firm"
on public.runs for update to authenticated
using (firm_id = public.current_firm_id())
with check (firm_id = public.current_firm_id());

create policy "runs: delete own firm"
on public.runs for delete to authenticated
using (firm_id = public.current_firm_id());

-- ---------------------------------------------------------------------------
-- reports — full CRUD within the caller's firm
-- ---------------------------------------------------------------------------
create policy "reports: read own firm"
on public.reports for select to authenticated
using (firm_id = public.current_firm_id());

create policy "reports: insert into own firm"
on public.reports for insert to authenticated
with check (firm_id = public.current_firm_id());

create policy "reports: update own firm"
on public.reports for update to authenticated
using (firm_id = public.current_firm_id())
with check (firm_id = public.current_firm_id());

create policy "reports: delete own firm"
on public.reports for delete to authenticated
using (firm_id = public.current_firm_id());
