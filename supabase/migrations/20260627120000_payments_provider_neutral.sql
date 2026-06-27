-- Provider-neutral payment columns — so the billing layer isn't hardcoded to Paddle.
--
-- We now support more than one Merchant of Record (Paddle + Dodo Payments), picked by the
-- NEXT_PUBLIC_PAYMENT_PROVIDER switch in the app. This migration renames the Paddle-specific
-- columns added by 20260625120000_paddle_billing.sql to neutral `payment_*` names and records
-- which provider owns each record (`payment_provider`). The entitlement gate
-- (`public.firm_can_download`), the pilot/complimentary logic, and `grant_pilot_firm` are
-- unaffected — they never reference these columns. Runs once, after the Paddle billing
-- migration, during `supabase db push` (see docs/PAYMENTS.md, docs/MIGRATIONS.md).

-- 1) firms: rename the Paddle-specific subscription columns to neutral names.
alter table public.firms rename column paddle_customer_id to payment_customer_id;
alter table public.firms rename column paddle_subscription_id to payment_subscription_id;

-- 2) design_credits: rename the Paddle transaction id to a neutral name.
alter table public.design_credits rename column paddle_transaction_id to payment_transaction_id;

-- 3) Record which Merchant of Record owns each record (e.g. 'paddle' | 'dodo').
alter table public.firms add column if not exists payment_provider text;
alter table public.design_credits add column if not exists payment_provider text;
