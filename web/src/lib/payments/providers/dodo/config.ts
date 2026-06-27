/**
 * Dodo Payments configuration — a Merchant-of-Record that onboards South African sellers fast
 * and covers the EU. All IDs come from env so the same code runs against the test environment
 * now and live later (just swap the env values). See docs/PAYMENTS.md for setup.
 *
 * Unlike Paddle, Dodo creates the checkout session server-side, so the API key + product IDs are
 * server-only (NOT NEXT_PUBLIC). Only `NEXT_PUBLIC_DODO_ENV` is public (it picks the API host).
 */

export type DodoEnvironment = "test" | "live";

export const DODO_ENV: DodoEnvironment =
  process.env.NEXT_PUBLIC_DODO_ENV === "live" ? "live" : "test";

export const DODO_API_BASE =
  DODO_ENV === "live" ? "https://live.dodopayments.com" : "https://test.dodopayments.com";

/** Server-side API key (Bearer) used to create checkout sessions. */
export const DODO_API_KEY = process.env.DODO_API_KEY ?? "";

/** Dodo product IDs. A subscription product creates a subscription; a one-time product a payment. */
export const DODO_PRODUCTS = {
  /** Firm subscription — R1,650/mo recurring. */
  firmMonthly: process.env.DODO_PRODUCT_FIRM_MONTHLY ?? "",
  /** Pay-as-you-go — R250 one-off per calc package. */
  calcPackage: process.env.DODO_PRODUCT_CALC_PACKAGE ?? "",
} as const;

/**
 * Recurring discount code applied for pilot firms (→ R999/mo). Pre-applied at checkout for firms
 * we've marked `is_pilot`; never surfaced as a public coupon.
 */
export const DODO_PILOT_DISCOUNT_CODE = process.env.DODO_DISCOUNT_PILOT ?? "";

/** True once the server-side Dodo config is present (API key + both products). */
export function dodoConfigured(): boolean {
  return Boolean(DODO_API_KEY && DODO_PRODUCTS.firmMonthly && DODO_PRODUCTS.calcPackage);
}
