# Paddle integration — setup & how it works

> **Status:** building in **sandbox** (live account pending KYB). Same code runs against
> production later — you only swap the env values. Pricing model: `docs/PRICING.md`.

## How it works (the model)

- **Free** — calculate + Check mode + on-screen results. No PDF download.
- **Firm subscription** — R1,650/mo (Paddle recurring). Unlocks unlimited calc-package
  downloads while `subscription_status` is `active`/`trialing`.
- **Founding firms** — we mark the firm `is_founding` and grant a **no-card complimentary
  month** (`complimentary_until`), so a pilot can validate against past projects with zero
  friction. When they continue, checkout opens with the **founding recurring discount**
  pre-applied → **R999/mo for 12 cycles**, then auto-reverts to R1,650.
- **Pay-as-you-go** — R250 one-off per calc package (Paddle one-time transaction). A paid
  `design_credit` unlocks that one design's PDF forever (re-downloads/revisions free).

The **gate** is the calc-package PDF download: `public.firm_can_download(run_id)` returns true
for an active/trialing subscription, a live complimentary window, or a PAYG credit for that run.

## One-time founder setup (Paddle sandbox dashboard)

1. Create a **sandbox** account at `sandbox-vendors.paddle.com` (separate from live).
2. **Catalog → Products**:
   - "TorenOne Firm subscription" → add a **recurring** price **R1,650 / month** → note the
     price ID `pri_…` → `NEXT_PUBLIC_PADDLE_PRICE_FIRM_MONTHLY`.
   - "TorenOne calc package" → add a **one-time** price **R250** → note `pri_…` →
     `NEXT_PUBLIC_PADDLE_PRICE_CALC_PACKAGE`.
3. **Catalog → Discounts** → create a **recurring** discount, **amount R651 off** (R1,650 →
   R999), **recurs for 12 billing periods**, restricted to the Firm price → note `dsc_…` →
   `NEXT_PUBLIC_PADDLE_DISCOUNT_FOUNDING`.
4. **Developer Tools → Authentication** → create a **client-side token** (`test_…`) →
   `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN`. (Optional: an API key for server calls → `PADDLE_API_KEY`.)
5. **Developer Tools → Notifications** → add a destination at
   `https://<your-site>/api/paddle/webhook`, subscribe to `subscription.created`,
   `subscription.updated`, `subscription.canceled`, `transaction.completed` → note the secret →
   `PADDLE_WEBHOOK_SECRET`.

## Environment variables

```
# Client (safe to expose)
NEXT_PUBLIC_PADDLE_ENV=sandbox            # or "production"
NEXT_PUBLIC_PADDLE_CLIENT_TOKEN=test_xxx
NEXT_PUBLIC_PADDLE_PRICE_FIRM_MONTHLY=pri_xxx
NEXT_PUBLIC_PADDLE_PRICE_CALC_PACKAGE=pri_xxx
NEXT_PUBLIC_PADDLE_DISCOUNT_FOUNDING=dsc_xxx
# Server-only (webhook + admin DB writes)
PADDLE_WEBHOOK_SECRET=pdl_ntfset_xxx
SUPABASE_SERVICE_ROLE_KEY=...             # already set for invites; the webhook reuses it
```

Until these are set the app degrades gracefully: the pricing CTAs show a "billing not
configured yet" state and nothing breaks.

## Granting a founding firm

Run once per pilot firm (service role / SQL editor):

```sql
select public.grant_founding_firm('<firm-uuid>', 30);  -- 30-day no-card complimentary trial
```

## Local webhook testing

Paddle must reach `/api/paddle/webhook` over HTTPS. Either use Paddle's **simulate** feature
in Notifications, or tunnel locally with `cloudflared tunnel --url http://localhost:3000` and
point the sandbox destination at the tunnel URL.
