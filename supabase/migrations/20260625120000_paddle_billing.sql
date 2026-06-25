-- Paddle billing (docs/PADDLE.md, docs/PRICING.md).
--
-- Plan model: `free` (calculate + Check mode, no PDF download), the `firm` subscription
-- (R1,650/mo; founding firms get a no-card complimentary trial + a R999 12-month discount),
-- and pay-as-you-go (R250 one-off per calc package). The "entitlement" is what unlocks
-- downloading a calc-package PDF — the toll gate. Subscription state is written by the
-- Paddle webhook via the service role; clients only ever read.

-- ---------------------------------------------------------------------------
-- Firm-level subscription / entitlement state
-- ---------------------------------------------------------------------------
alter table public.firms
    add column if not exists plan text not null default 'free'
        check (plan in ('free', 'firm')),
    add column if not exists is_founding boolean not null default false,
    add column if not exists paddle_customer_id text,
    add column if not exists paddle_subscription_id text,
    add column if not exists subscription_status text
        check (subscription_status in ('trialing', 'active', 'past_due', 'paused', 'canceled')),
    add column if not exists subscription_current_period_end timestamptz,
    -- Complimentary (no-card) access window — the founding pilot trial we grant directly,
    -- so a skeptical engineer can validate against past projects before any card is asked for.
    add column if not exists complimentary_until timestamptz;

-- ---------------------------------------------------------------------------
-- Pay-as-you-go credits — one paid calc package unlocks that run's PDF forever
-- (re-downloads + minor revisions stay free, per the Refund & Cancellation Policy).
-- ---------------------------------------------------------------------------
create table if not exists public.design_credits (
    id                    uuid primary key default gen_random_uuid(),
    run_id                uuid not null references public.runs (id) on delete cascade,
    firm_id               uuid not null references public.firms (id) on delete cascade,
    paddle_transaction_id text,
    created_by            uuid references public.profiles (id) on delete set null,
    created_at            timestamptz not null default now(),
    unique (run_id)
);
create index if not exists design_credits_firm_id_idx on public.design_credits (firm_id);

-- RLS: a firm reads only its own credits; inserts come from the webhook (service role,
-- which bypasses RLS). Default-deny for everything else.
alter table public.design_credits enable row level security;

drop policy if exists design_credits_select_own on public.design_credits;
create policy design_credits_select_own on public.design_credits
    for select to authenticated
    using (firm_id = public.current_firm_id());

-- ---------------------------------------------------------------------------
-- Entitlement helper — can the caller's firm download `p_run_id`'s calc package?
-- True if (a) an active/trialing Firm subscription, (b) a live complimentary window, or
-- (c) a paid PAYG credit for that specific design. SECURITY DEFINER + pinned search_path
-- (the Supabase pattern), reusing public.current_firm_id() from the storage migration.
-- ---------------------------------------------------------------------------
create or replace function public.firm_can_download(p_run_id uuid)
returns boolean
language sql
security definer
set search_path = ''
stable
as $$
    select exists (
        select 1
        from public.firms f
        where f.id = public.current_firm_id()
          and (
              f.subscription_status in ('trialing', 'active')
              or (f.complimentary_until is not null and f.complimentary_until > now())
          )
    )
    or exists (
        select 1
        from public.design_credits c
        where c.run_id = p_run_id
          and c.firm_id = public.current_firm_id()
    );
$$;

-- ---------------------------------------------------------------------------
-- Admin grant — mark a firm `founding` + open a no-card complimentary trial window.
-- Called by us (service role / SQL) for pilot firms; NOT exposed to anon/authenticated.
-- ---------------------------------------------------------------------------
create or replace function public.grant_founding_firm(p_firm_id uuid, p_trial_days int default 30)
returns void
language sql
security definer
set search_path = ''
as $$
    update public.firms
    set is_founding = true,
        complimentary_until =
            greatest(coalesce(complimentary_until, now()), now()) + make_interval(days => p_trial_days)
    where id = p_firm_id;
$$;

revoke all on function public.grant_founding_firm(uuid, int) from public, anon, authenticated;
