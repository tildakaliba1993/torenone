/**
 * Paddle (Billing) configuration — all IDs come from env so nothing is hard-coded and the
 * same code runs against sandbox now and production later (just swap the env values).
 *
 * Client-side values are NEXT_PUBLIC_ (the Paddle client token and price/discount IDs are
 * public by design — they only open a checkout). Secrets (webhook signing key) are server-only
 * and live in ./server.ts. See docs/PAYMENTS.md for setup.
 */

export type PaddleEnvironment = "sandbox" | "production";

export const PADDLE_ENV: PaddleEnvironment =
  process.env.NEXT_PUBLIC_PADDLE_ENV === "production" ? "production" : "sandbox";

export const PADDLE_CLIENT_TOKEN = process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN ?? "";

/** Paddle price IDs (pri_...). */
export const PADDLE_PRICES = {
  /** Firm subscription — R1,650/mo recurring, no trial. Pilot firms get R999 via the discount. */
  firmMonthly: process.env.NEXT_PUBLIC_PADDLE_PRICE_FIRM_MONTHLY ?? "",
  /** Pay-as-you-go — R250 one-off per calc package. */
  calcPackage: process.env.NEXT_PUBLIC_PADDLE_PRICE_CALC_PACKAGE ?? "",
} as const;

/**
 * Recurring discount (dsc_...) applied for pilot firms — takes the Firm price R1,650 → R999
 * for 12 billing cycles, then it auto-reverts. Pre-applied at checkout for firms we've marked
 * `is_pilot`; never shown as a public coupon code.
 */
export const PADDLE_PILOT_DISCOUNT_ID = process.env.NEXT_PUBLIC_PADDLE_DISCOUNT_PILOT ?? "";

/** True once the client-side Paddle config is present (token + both prices). */
export function paddleConfigured(): boolean {
  return Boolean(PADDLE_CLIENT_TOKEN && PADDLE_PRICES.firmMonthly && PADDLE_PRICES.calcPackage);
}
