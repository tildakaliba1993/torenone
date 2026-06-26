# Paddle integration — setup & how it works

> **Status:** building in **sandbox** (live account pending KYB). Same code runs against
> production later — you only swap the env values. Pricing model: `docs/PRICING.md`.

## How it works (the model)

- **Free** — calculate + Check mode + on-screen results. No PDF download.
- **Firm subscription** — R1,650/mo (Paddle recurring). Unlocks unlimited calc-package
  downloads while `subscription_status` is `active`/`trialing`.
- **Pilot firms** — marked `is_pilot` with a **no-credit-card complimentary month**
  (`complimentary_until`), granted automatically when they sign up with a valid pilot access
  code (or via `grant_pilot_firm`). They validate against past projects with zero card. When
  they continue, checkout opens with the **pilot recurring discount** pre-applied →
  **R999/mo for 12 cycles**, then auto-reverts to R1,650.
- **Pay-as-you-go** — R250 one-off per calc package (Paddle one-time transaction). A paid
  `design_credit` unlocks that one design's PDF forever (re-downloads/revisions free).

The **gate** is the calc-package PDF download: `public.firm_can_download(run_id)` returns true
for an active/trialing subscription, a live complimentary window, or a PAYG credit for that run.

## One-time founder setup (Paddle sandbox dashboard)

1. Create a **sandbox** account at `sandbox-vendors.paddle.com` (separate from live).
2. **Catalog → Products**:
   - "TorenOne Firm subscription" → a **recurring** price **R1,650/mo, no trial** →
     `NEXT_PUBLIC_PADDLE_PRICE_FIRM_MONTHLY`. (A trial-bearing price is **not** used — pilot
     firms get their free month as a no-credit-card grant, below; any trial price can be archived.)
   - "TorenOne calc package" → a **one-time** price **R250** → `NEXT_PUBLIC_PADDLE_PRICE_CALC_PACKAGE`.
3. **Catalog → Discounts** → create a **recurring** discount, **amount R651 off** (R1,650 →
   R999), **recurs for 12 billing periods** → note `dsc_…` → `NEXT_PUBLIC_PADDLE_DISCOUNT_PILOT`.
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
NEXT_PUBLIC_PADDLE_PRICE_FIRM_MONTHLY=pri_xxx     # R1,650/mo, no trial
NEXT_PUBLIC_PADDLE_PRICE_CALC_PACKAGE=pri_xxx
NEXT_PUBLIC_PADDLE_DISCOUNT_PILOT=dsc_xxx
# Server-only (webhook + admin DB writes)
PADDLE_WEBHOOK_SECRET=pdl_ntfset_xxx
SUPABASE_SERVICE_ROLE_KEY=...             # already set for invites; the webhook reuses it
```

Until these are set the app degrades gracefully: the pricing CTAs show a "billing not
configured yet" state and nothing breaks.

### Where do these go?

- **Local development:** put **all** of them in **`web/.env.local`** — Next.js reads that
  single file for both the `NEXT_PUBLIC_*` (browser) vars **and** the server-only ones (the
  webhook route + admin client run inside the Next server). They do **not** go in the
  engineering service's `.env` (a separate process). Restart `npm run dev` after editing.
- **Production (later):** the same keys go in **Netlify → Site settings → Environment
  variables**. `NEXT_PUBLIC_*` are exposed to the browser (fine — they only open a checkout);
  the others stay server-side.

### Which value is which (from the Paddle dashboard)

| Env var | Where to find it in Paddle |
|---|---|
| `NEXT_PUBLIC_PADDLE_PRICE_FIRM_MONTHLY` | Catalog → the Firm product → the **R1,650/mo price with *no* trial** (`pri_…`). |
| `NEXT_PUBLIC_PADDLE_PRICE_CALC_PACKAGE` | Catalog → the **R250 one-off** price (`pri_…`). |
| `NEXT_PUBLIC_PADDLE_DISCOUNT_PILOT` | Discounts → open your pilot discount (your **"Founding Firm Discount"**) → copy its `dsc_…` id. |
| `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN` | Developer Tools → **Authentication → Client-side tokens** → your token. |
| `PADDLE_WEBHOOK_SECRET` | Developer Tools → **Notifications** → open your destination → reveal the secret (`pdl_ntfset_…`). |
| `SUPABASE_SERVICE_ROLE_KEY` | Already in the repo's root `.env`; the webhook reuses it. |

> **One Firm price; no credit card for pilots.** Everyone checks out on the **standard**
> R1,650/mo price (no Paddle trial). Pilot firms get the **discount** applied → **R999/mo** for
> 12 cycles. Their **free month is a no-credit-card grant** — so a pilot validates with **zero
> card**, and only enters one if/when they choose to subscribe at R999.

## Pilot firms — how they're identified & granted

A firm becomes a pilot (`firms.is_pilot = true` + a complimentary window) in one of two ways:

1. **Automatic, via a pilot access code (recommended).** Create a code we hand only to vetted
   firms; signing up with it auto-grants the pilot trial. Insert codes (service role / SQL editor):
   ```sql
   insert into public.pilot_codes (code, label, complimentary_days, max_uses)
   values ('CPT-PILOT-2026', 'Cape Town cohort', 30, 25);
   ```
   Share the link `https://torenone.com/signup?pilot=CPT-PILOT-2026` (the code pre-fills the
   "Pilot access code" field), or have them type it at sign-up. The signup trigger validates the
   code (active + under `max_uses`) and grants the no-credit-card month automatically.
2. **Manual,** for a one-off:
   ```sql
   select public.grant_pilot_firm('<firm-uuid>', 30);  -- 30-day no-credit-card complimentary window
   ```

To see who's a pilot: `select id, name, is_pilot, complimentary_until from public.firms where is_pilot;`

## Testing it locally — full checklist

1. **Apply the migration** to your Supabase project (adds the billing columns + entitlement
   function): from the repo root, `supabase db push`. Until this runs, the Billing card still
   shows but the gate "fails open" (downloads aren't enforced).
2. **Set the env vars** in `web/.env.local` (above) and **restart `npm run dev`**.
3. **Open the checkout:** sign in → Account → Billing → "Subscribe", or hit the pricing page's
   "Get the Firm plan". The Paddle overlay should open with the R1,650 price (or R999 once the
   firm is a pilot — see above). Use Paddle's **test card** `4242 4242 4242 4242`.
4. **Webhook:** Paddle must reach `POST /api/paddle/webhook` over HTTPS. Tunnel your local web:
   ```
   cloudflared tunnel --url http://localhost:3000        # or ngrok http 3000
   ```
   Then in Paddle → Notifications, set the destination URL to
   `https://<your-tunnel>/api/paddle/webhook` (the path matters), subscribe to
   `subscription.*` + `transaction.completed`, and make sure the destination's **secret matches
   `PADDLE_WEBHOOK_SECRET`**. After a successful checkout the webhook flips the firm to
   `active` and downloads unlock. (No tunnel handy? Use Paddle's **Simulate** on the
   destination to fire a sample event.)
5. **Pilot flow:** grant the firm (above), reload Account → it shows "Pilot trial active",
   downloads work with no credit card; "Continue at R999/mo" opens checkout with the discount applied.
