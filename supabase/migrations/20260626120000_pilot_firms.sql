-- Pilot firms (was "founding") — rename + automated grant via an access code.
--
-- We hand a pilot access code only to firms we've vetted. Signing up with a valid code
-- auto-marks the firm a pilot and opens a no-credit-card complimentary window — so a pilot
-- validates against past projects with zero card, and we never run SQL per firm. Without a
-- valid code, sign-up is unchanged (a normal firm). See docs/PADDLE.md.

-- 1) Rename the firm flag (20260625 always creates `is_founding` before this migration runs).
alter table public.firms rename column is_founding to is_pilot;
drop function if exists public.grant_founding_firm(uuid, int);

-- 2) Pilot access codes. Read only via the SECURITY DEFINER sign-up trigger / service role;
--    RLS is enabled with no policies, so clients (anon/authenticated) never see the codes.
create table if not exists public.pilot_codes (
    id                 uuid primary key default gen_random_uuid(),
    code               text not null unique,
    label              text,
    complimentary_days int not null default 30,
    active             boolean not null default true,
    max_uses           int,                       -- null = unlimited
    uses               int not null default 0,
    created_at         timestamptz not null default now()
);
alter table public.pilot_codes enable row level security;

-- 3) Admin grant — mark a firm a pilot + open a no-credit-card complimentary window.
create or replace function public.grant_pilot_firm(p_firm_id uuid, p_trial_days int default 30)
returns void
language sql
security definer
set search_path = ''
as $$
    update public.firms
    set is_pilot = true,
        complimentary_until =
            greatest(coalesce(complimentary_until, now()), now()) + make_interval(days => p_trial_days)
    where id = p_firm_id;
$$;
revoke all on function public.grant_pilot_firm(uuid, int) from public, anon, authenticated;

-- 4) Auto-grant on sign-up: honour a pilot access code in the new firm's bootstrap. Normal
--    sign-ups (no code) are unchanged.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_firm_id    uuid;
    v_firm_name  text;
    v_role       text;
    v_pilot_code text;
    v_pilot_days int;
begin
    v_firm_id := nullif(new.raw_user_meta_data ->> 'firm_id', '')::uuid;

    if v_firm_id is null then
        -- First user of a new firm: create the firm; this user owns it.
        v_firm_name := coalesce(
            nullif(new.raw_user_meta_data ->> 'firm_name', ''),
            'Firm of ' || coalesce(new.email, new.id::text)
        );

        -- Valid pilot access code? (active, not exhausted)
        v_pilot_code := nullif(new.raw_user_meta_data ->> 'pilot_code', '');
        if v_pilot_code is not null then
            select complimentary_days into v_pilot_days
            from public.pilot_codes
            where code = v_pilot_code
              and active
              and (max_uses is null or uses < max_uses)
            limit 1;
        end if;

        if v_pilot_days is not null then
            insert into public.firms (name, is_pilot, complimentary_until)
            values (v_firm_name, true, now() + make_interval(days => v_pilot_days))
            returning id into v_firm_id;
            update public.pilot_codes set uses = uses + 1 where code = v_pilot_code;
        else
            insert into public.firms (name)
            values (v_firm_name)
            returning id into v_firm_id;
        end if;

        v_role := 'owner';
    else
        v_role := 'engineer';
    end if;

    insert into public.profiles (id, firm_id, name, role)
    values (
        new.id,
        v_firm_id,
        nullif(new.raw_user_meta_data ->> 'full_name', ''),
        v_role
    );

    return new;
end;
$$;
