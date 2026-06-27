# Payments — pluggable Merchant-of-Record providers

TorenOne's billing is **not hardcoded to one provider**. Payment providers are **switches**: one
is active at a time, chosen by a single env var, and you can swap them **without changing code**.

- **Paddle** — the original Merchant of Record. Full setup: [`docs/PADDLE.md`](./PADDLE.md).
- **Dodo Payments** — a Merchant of Record that **onboards South African sellers fast** (same-day
  KYB) and covers the EU. Added because Paddle KYB for FINCREST PTY LTD dragged on. Setup below.

Both are **Merchants of Record** — they collect + remit SA→EU VAT, so we don't. The pricing model
(Free · R250 PAYG · R1,650/mo Firm · R999 pilot + free no-credit-card month) is unchanged across
providers — see [`docs/PRICING.md`](./PRICING.md).

## The switch

```
NEXT_PUBLIC_PAYMENT_PROVIDER=paddle   # or "dodo" (default: paddle)
```

Set this (plus the active provider's keys, below) and restart `npm run dev` / redeploy. That's it —
the Billing card, the pay-as-you-go flow, the entitlement gate, and the DB are all provider-agnostic.
**One provider is active at a time.** Flip to `dodo` while/after Paddle KYB clears.

## Architecture (where things live)

```
web/src/lib/payments/
  config.ts        — PAYMENT_PROVIDER switch (reads NEXT_PUBLIC_PAYMENT_PROVIDER)
  types.ts         — the adapter interface + neutral CheckoutDirective / event types
  actions.ts       — "use server": createSubscriptionCheckout / createPackageCheckout / isPaymentConfigured
  client.ts        — "use client": beginCheckout(directive) — redirect OR open the Paddle overlay
  entitlements.ts  — the ONE place that writes entitlement state (firms / design_credits)
  providers/
    paddle/        — config + checkout (overlay directive) + server (Paddle-Signature verify + normalize)
    dodo/          — config + checkout (server REST session → redirect) + server (Standard Webhooks + normalize)
web/src/app/api/paddle/webhook/route.ts   — verifies + normalizes → entitlements
web/src/app/api/dodo/webhook/route.ts     — verifies + normalizes → entitlements
```

**Checkout differs by provider, hidden behind one directive:** Paddle opens a client-side overlay
(Paddle.js); Dodo creates a hosted session server-side and we redirect to its `checkout_url`. The
server action returns a `CheckoutDirective`; the client's `beginCheckout` does the right thing.

**Webhooks stay per-provider** (each dashboard points at its own URL) but both normalize into the
same `applyNormalizedEvent` handler. Keep both routes mounted — the inactive provider just sends no
traffic.

**DB is provider-neutral:** `firms.payment_customer_id` / `payment_subscription_id` /
`payment_provider`, and `design_credits.payment_transaction_id` / `payment_provider`
(migration `20260627120000_payments_provider_neutral.sql`, applied after the Paddle billing
migration). The entitlement gate `public.firm_can_download` and all pilot logic are unchanged.

**Adding a third provider** = add `providers/<name>/{config,checkout,server}.ts` implementing the
adapter, a branch in `actions.ts`, a webhook route, and a `payment_provider` value. No UI/DB churn.

## Dodo Payments — setup

### Environment variables (`web/.env.local`; prod → Netlify env)

```
NEXT_PUBLIC_PAYMENT_PROVIDER=dodo     # make Dodo the active provider
NEXT_PUBLIC_DODO_ENV=test             # or "live"
DODO_API_KEY=                         # server-only — creates checkout sessions
DODO_PRODUCT_FIRM_MONTHLY=            # subscription product id (R1,650/mo)
DODO_PRODUCT_CALC_PACKAGE=            # one-time product id (R250)
DODO_DISCOUNT_PILOT=                  # recurring discount code → R999/mo for pilots (optional)
DODO_WEBHOOK_SECRET=                  # server-only — Standard Webhooks signing secret (whsec_…)
SUPABASE_SERVICE_ROLE_KEY=            # already set; the webhook reuses it to write entitlements
```

Only `NEXT_PUBLIC_*` reach the browser. The API key, product ids, and webhook secret are
**server-only** (unlike Paddle, Dodo creates the checkout server-side).

### Dashboard steps

1. Create a Dodo account; verify the business — **South African companies are supported**, and KYB
   is typically same-day (the reason we added Dodo). Use **FINCREST PTY LTD** (see
   [`docs/SESSION_HANDOFF.md`](./SESSION_HANDOFF.md) / the legal entity note).
2. **Products** → create a **subscription** product **R1,650/mo** → `DODO_PRODUCT_FIRM_MONTHLY`;
   and a **one-time** product **R250** → `DODO_PRODUCT_CALC_PACKAGE`.
3. **Discounts** → a recurring discount taking R1,650 → **R999** → its code/id →
   `DODO_DISCOUNT_PILOT`.
4. **API key** → `DODO_API_KEY`. Pick test vs live with `NEXT_PUBLIC_DODO_ENV`
   (`test.dodopayments.com` vs `live.dodopayments.com`).
5. **Webhook** → add a destination `https://<your-site>/api/dodo/webhook`, subscribe to
   `subscription.*` and `payment.succeeded`, copy the signing secret → `DODO_WEBHOOK_SECRET`.

### Test locally

1. Apply migrations from the repo root: `supabase db push` (billing + pilot + provider-neutral).
   Until applied the gate **fails open** (downloads still work).
2. `NEXT_PUBLIC_PAYMENT_PROVIDER=dodo` + the Dodo keys in `web/.env.local`; restart `npm run dev`.
3. Account → Billing → "Subscribe" (or the pricing CTA) → you should be **redirected** to a Dodo
   checkout. PAYG: download a calc package while unentitled → redirected to a R250 Dodo checkout.
4. Webhook: tunnel (`cloudflared tunnel --url http://localhost:3000`), point the Dodo destination at
   `https://<tunnel>/api/dodo/webhook`. After checkout the firm flips to `active` and downloads unlock.

> The exact request/response field names in Dodo's checkout API can shift between versions; the
> adapter reads the URL from `checkout_url` / `url` / `payment_link` defensively. If a live call
> returns an unexpected shape, adjust `web/src/lib/payments/providers/dodo/checkout.ts`.

## Pilot firms (provider-independent)

Pilot status (`firms.is_pilot` + a complimentary window) is granted at sign-up via a **pilot access
code** or manually — see [`docs/PADDLE.md`](./PADDLE.md#pilot-firms--how-theyre-identified--granted).
The free month is a **no-credit-card grant**, not a provider trial; pilots only enter a card if they
choose to subscribe (then they get the R999 discount on the active provider).
