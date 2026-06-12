-- Minimal Supabase-compatible stubs so the TorenOne migrations apply + run on a
-- plain Postgres in tests (no Supabase stack / Docker required).
--
-- This is TEST INFRASTRUCTURE ONLY — it is never applied to a real Supabase project,
-- where `auth` / `storage` and these roles already exist. It recreates just enough:
--   * the anon / authenticated / service_role roles,
--   * an `auth.users` table + `auth.uid()` reading the JWT-claims GUC,
--   * a `storage` schema with buckets/objects + `storage.foldername()`,
-- so that the real migrations (and their RLS policies) behave exactly as in production.

create extension if not exists pgcrypto;

-- Supabase API roles (cluster-global; create-if-missing so reruns are safe).
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon nologin noinherit;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated nologin noinherit;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'service_role') then
        create role service_role nologin noinherit bypassrls;
    end if;
end
$$;

-- auth schema: users table + uid()/role() reading the request JWT claims, exactly the
-- contract the migrations rely on (auth.uid() -> the signed-in user's uuid).
create schema if not exists auth;

-- Columns mirror the subset of Supabase's real auth.users that seed.sql populates,
-- so the same seed applies here in tests (the real table has many more columns; all
-- the extras we omit are nullable / defaulted in Supabase).
create table if not exists auth.users (
    id                  uuid primary key default gen_random_uuid(),
    instance_id         uuid,
    aud                 text,
    role                text,
    email               text,
    encrypted_password  text,
    email_confirmed_at  timestamptz,
    raw_app_meta_data   jsonb not null default '{}'::jsonb,
    raw_user_meta_data  jsonb not null default '{}'::jsonb,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);

create or replace function auth.uid()
returns uuid
language sql
stable
as $$
    select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

create or replace function auth.role()
returns text
language sql
stable
as $$
    select coalesce(nullif(current_setting('request.jwt.claim.role', true), ''), 'anon')
$$;

-- storage schema: just enough for the Task 5.3 bucket + object policies.
create schema if not exists storage;

create table if not exists storage.buckets (
    id      text primary key,
    name    text not null,
    public  boolean not null default false
);

create table if not exists storage.objects (
    id          uuid primary key default gen_random_uuid(),
    bucket_id   text references storage.buckets (id),
    name        text,
    owner       uuid
);

create or replace function storage.foldername(name text)
returns text[]
language sql
immutable
as $$
    select string_to_array(name, '/')
$$;

-- Grant the API roles schema/table access (RLS still narrows what they can see).
grant usage on schema public, auth, storage to anon, authenticated, service_role;
grant select, insert, update, delete on storage.objects to anon, authenticated;
grant select on storage.buckets to anon, authenticated;

-- Tables created by the migrations (run as this same role) inherit these DML grants.
alter default privileges in schema public
    grant select, insert, update, delete on tables to anon, authenticated;
