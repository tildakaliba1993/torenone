# TorenOne — Pricing & Monetisation Plan

> **Status:** agreed direction (2026-06-24), founder-approved. **Not yet built** — the
> payment integration is intentionally deferred (see [§ Build trigger](#build-trigger--sequencing)).
> The co-founder engineering **validation gate** (`docs/PRODUCTION_READINESS.md` §1) remains the
> real blocker to any live revenue.

## 1. The model — "Pay-for-the-PDF" (outcome-based)

We charge for the **completed work** (the stamp-ready calc package), not for **access** to the
tool. This explicitly **rejects the incumbent per-seat model** (Prokon / ETABS ~R75k per seat
per year) — that pricing is exactly what we're disrupting as a YC "SaaS Challenger."

| Stage | What the engineer can do | Price |
|---|---|---|
| **Free — "calculate"** | Sign up, parse a frame, run the kernel, see on-screen results (sections, utilisations, tonnage, BMD/SFD), **unlimited Check mode** | **R0** |
| **Toll gate — the calc package** | Download the 15-page, clause-referenced, stamp-ready PDF | **PAYG R250 (~$15) / design**, or a subscription |
| **Firm subscription** | The whole firm (unlimited seats), effectively-unlimited calc packages | **R1,650 (~$99) / mo** standard · **R999 / mo** pilot (locked year 1) |

**Why this model:** marginal cost per design ≈ cents (one OpenAI parse + a few CPU-seconds +
a stored PDF) ⇒ **>95% gross margin**. So we compete on conversion + value capture, not cost.
Charging only for the deliverable (not per run) **kills "run anxiety"** — engineers iterate
freely on-screen and pay once, at peak value — and turns **Check mode into pure lead-gen**
(they use the free tool to double-check their own Prokon/ETABS work, see the numbers match,
and trust us). A skeptical structural engineer will never hit a credit-card wall *before* they
see the math works; this model removes that wall.

## 2. Refinements (agreed, over the raw proposal)

1. **The paid unit is a calc package _per design_, not per PDF click.** Once a design is paid
   for, **re-downloads and minor revisions of that design are free.** Charging again for a
   re-download (e.g. after the reviewing Pr.Eng asks for a tweak, under a municipal deadline)
   would feel like nickel-and-diming. Credits deplete on **finalise**, not on each download.
2. **No restrictive PDF cap on the firm plan.** A "10 PDFs/mo" cap reintroduces metering and
   makes the subscription barely cheaper than PAYG (R165 vs R250/pkg) — so few would upgrade.
   Make the firm plan **effectively unlimited** (or cap so high, e.g. 30–50, that it never
   bites a normal firm). The subscription must be an obvious win at the firm's natural volume.
3. **Free-tier run quota.** "Free to run unlimited" is the one real cost leak — every parse
   hits OpenAI ($). Add a **generous free quota** (~20 parses/designs per firm per month) to
   bound exposure. (Rate limits + the per-request output-token cap already exist; this is the
   account-level floor.) The on-screen result is the value; 20/mo is plenty to evaluate.
4. **R250 is an intro price** — deliberately cheap (~12–20× ROI vs ~R3–5k of junior
   labour per frame) to maximise land + trust. Keep headroom to raise later.
5. **Checkout liability copy.** State that the fee is for **generating the document / saving
   time, not certifying the design** — the engineer still reviews, verifies and stamps (the PDF
   cover already carries this disclaimer). Removes any implication we take on engineering
   liability for payment.

## 3. The pitch (for sales / landing copy)

- To an individual engineer: *"Pay R250 to skip 2 days of junior-engineer labour. Run it free,
  check the numbers against your own work, and only pay when you need the stamp-ready report."*
- To a firm: *"Prokon costs ~R75,000/year for **one** engineer. TorenOne is R19,800/year for
  your **entire firm** — and it writes the calc package for you."*

## 4. Payments

- **Provider: pluggable Merchant of Record (Paddle + Dodo Payments).** An MoR absorbs SA→EU
  VAT/sales-tax compliance, impractical to handle directly from a SA entity at MVP. Providers are
  **switchable via `NEXT_PUBLIC_PAYMENT_PROVIDER`** (one active at a time) — see `docs/PAYMENTS.md`.
- **Why two:** Paddle KYB for the SA entity dragged on, so we added **Dodo Payments** (MoR that
  onboards SA sellers fast / same-day KYB, EU-ready). Flip to Dodo while/after Paddle clears.
- **Diligence BEFORE going live:** confirm the active provider **pays out to the SA entity**
  (historically the sticking point for non-UK/EU sellers). Not Stripe (no SA support).
- Decide the credit/grandfathering rules: credits deplete on **finalise** (per §2.1); free-tier
  downloads made before launch remain accessible.

## 5. Timing — phased, liability-aware

| Phase | When | Pricing | Goal |
|---|---|---|---|
| **1 — Historical validation** | Now (Phase 8 + start of pilot) | **Free** | Firms run *past, finished* projects through TorenOne to confirm our math matches theirs. Build **trust**. Don't charge for a favour. |
| **2 — LOI lock-in** | After a firm sees it works | **LOI, no checkout** | "We launch our public beta soon at R1,650/mo. Sign this non-binding LOI now and lock **R999/mo** for year 1." Secures commitment (YC traction) without checkout friction. |
| **3 — First live stamp** | When a firm uses TorenOne on a **live, billable** project | **Flip Paddle live** — R250 PAYG / R1,650 (R999 pilot) sub | The free ride ends the moment we save them billable hours on a real submission. |

## 6. Build trigger & sequencing

**Do not build the payment integration yet.** Rationale:
- The **co-founder validation gate** (`PRODUCTION_READINESS.md` §1 — incl. the wind method) is
  the blocker to *any* real-project revenue. Eng focus stays there.
- Phase 2 is carried by an **LOI (paper), not code** — no integration needed to secure
  commitment.
- The gate point is a **single function** (`getReportSignedUrl()` in
  `web/src/lib/api/service.ts`, plus the run-history "Download PDF" buttons), so it's ~1 day of
  work whenever we want it. Building payment infra ahead of a signed LOI is effort ahead of the
  signal.

**Build it the week before Phase 3.** When we do, the implementation is roughly:
- Paddle account + products (PAYG price, firm subscription); webhook → Supabase (entitlements /
  credits table, RLS-scoped per firm).
- Gate `getReportSignedUrl()` + the run-history download buttons on an active subscription **or**
  a credit for that design; everything up to and including the on-screen Results stays free.
- Pilot firms get free admin credits/entitlement so they never hit the wall during testing.
- Checkout liability copy (§2.5).
