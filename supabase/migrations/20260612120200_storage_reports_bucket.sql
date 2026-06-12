-- TorenOne report-PDF storage (Phase 5, Task 5.3) — Design §A.7 / A.8.
--
-- A single PRIVATE bucket `reports` holds the generated calc-package PDFs. Access is
-- scoped per firm by object path: every object is stored under `<firm_id>/<...>.pdf`,
-- and the Storage RLS policies below only let a caller read/write objects whose first
-- path segment equals their own firm_id. Combined with the private bucket (no public
-- URLs), a firm can never reach another firm's PDFs.
--
-- `public.current_firm_id()` is the shared helper that resolves the caller's firm from
-- their profile; the Task 5.4 table RLS policies reuse it. It is SECURITY DEFINER so it
-- can read `profiles` without being subject to (and recursing through) that table's own
-- RLS, and STABLE so the planner can cache it within a statement.

-- ---------------------------------------------------------------------------
-- Shared helper — the caller's firm_id (used here + by the Task 5.4 RLS policies)
-- ---------------------------------------------------------------------------
create or replace function public.current_firm_id()
returns uuid
language sql
stable
security definer
set search_path = ''
as $$
    select firm_id from public.profiles where id = auth.uid()
$$;

-- ---------------------------------------------------------------------------
-- Private bucket for report PDFs
-- ---------------------------------------------------------------------------
insert into storage.buckets (id, name, public)
values ('reports', 'reports', false)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Storage RLS — a firm can only touch objects under its own `<firm_id>/` prefix
-- ---------------------------------------------------------------------------
create policy "reports: firm members can read their objects"
on storage.objects
for select
to authenticated
using (
    bucket_id = 'reports'
    and (storage.foldername(name))[1] = public.current_firm_id()::text
);

create policy "reports: firm members can upload to their firm folder"
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'reports'
    and (storage.foldername(name))[1] = public.current_firm_id()::text
);

create policy "reports: firm members can delete their objects"
on storage.objects
for delete
to authenticated
using (
    bucket_id = 'reports'
    and (storage.foldername(name))[1] = public.current_firm_id()::text
);
