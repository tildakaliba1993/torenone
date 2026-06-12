-- TorenOne dev/seed data (Phase 5, Task 5.5) — LOCAL DEVELOPMENT ONLY.
--
-- Loaded by `supabase db reset` (see config.toml [db.seed]). NEVER run against a real
-- project: it inserts a known-password user. Everything is idempotent (ON CONFLICT DO
-- NOTHING), so a reset/re-run never duplicates rows.
--
-- The dev user is inserted into auth.users; the Task 5.2 sign-up trigger then creates
-- the dev firm + profile from the `firm_name`/`full_name` metadata. A sample project +
-- run are added under that firm so there is something to see immediately.

-- Fixed ids so dev tooling/tests can reference them:
--   user    11111111-1111-1111-1111-111111111111   (dev@torenone.test / devpassword123)
--   project 22222222-2222-2222-2222-222222222222
--   run     33333333-3333-3333-3333-333333333333

insert into auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at
)
values (
    '00000000-0000-0000-0000-000000000000',
    '11111111-1111-1111-1111-111111111111',
    'authenticated',
    'authenticated',
    'dev@torenone.test',
    crypt('devpassword123', gen_salt('bf')),
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"firm_name":"TorenOne Dev Firm","full_name":"Dev Engineer"}'::jsonb,
    now(),
    now()
)
on conflict (id) do nothing;

-- Sample project under the dev firm (firm_id resolved from the trigger-created profile).
insert into public.projects (id, firm_id, name, created_by)
select
    '22222222-2222-2222-2222-222222222222',
    p.firm_id,
    'Demo warehouse portal frame',
    p.id
from public.profiles p
where p.id = '11111111-1111-1111-1111-111111111111'
on conflict (id) do nothing;

-- Sample run on that project.
insert into public.runs (id, project_id, firm_id, frame_spec, mode, status, created_by)
select
    '33333333-3333-3333-3333-333333333333',
    '22222222-2222-2222-2222-222222222222',
    p.firm_id,
    '{}'::jsonb,
    'design',
    'pending',
    p.id
from public.profiles p
where p.id = '11111111-1111-1111-1111-111111111111'
on conflict (id) do nothing;
