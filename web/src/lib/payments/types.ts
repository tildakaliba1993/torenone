/**
 * Provider-neutral payment types — the contract every Merchant-of-Record adapter satisfies,
 * plus the normalized shapes the UI and webhook layers speak. Adding a provider means adding
 * an adapter under `providers/<name>/` and a branch in `config.ts`/`actions.ts` — no churn in
 * the UI, the entitlement gate, or the DB. See docs/PAYMENTS.md.
 */

export type PaymentProviderId = "paddle" | "dodo";

/** Our canonical subscription status — matches the `firms.subscription_status` check constraint. */
export type SubscriptionStatus = "trialing" | "active" | "past_due" | "paused" | "canceled";

/**
 * What the client must do to start a checkout. Two shapes because providers differ in *where*
 * checkout is created:
 * - `redirect` — the server created a hosted checkout session (Dodo and most MoRs); the client
 *   just navigates to `url`.
 * - `paddle-overlay` — Paddle opens a client-side overlay via Paddle.js (it needs the *public*
 *   client token + price IDs, which are safe to send to the browser).
 */
export type CheckoutDirective =
  | { type: "redirect"; url: string }
  | {
      type: "paddle-overlay";
      env: "sandbox" | "production";
      clientToken: string;
      priceId: string;
      discountId?: string;
      email: string;
      customData: Record<string, string>;
    };

/** A subscription lifecycle change, normalized across providers. */
export interface NormalizedSubscriptionEvent {
  kind: "subscription";
  provider: PaymentProviderId;
  firmId: string;
  customerId: string | null;
  subscriptionId: string;
  status: SubscriptionStatus | null;
  currentPeriodEnd: string | null;
}

/** A one-off pay-as-you-go calc-package purchase, normalized across providers. */
export interface NormalizedPackageEvent {
  kind: "package";
  provider: PaymentProviderId;
  firmId: string;
  runId: string;
  transactionId: string;
}

/** A normalized webhook event, or `null` for events we deliberately ignore / can't map. */
export type NormalizedEvent = NormalizedSubscriptionEvent | NormalizedPackageEvent | null;

export interface SubscriptionCheckoutInput {
  email: string;
  firmId: string;
  /** Pilot firms get the recurring discount pre-applied (→ R999/mo). */
  pilot: boolean;
}

export interface PackageCheckoutInput {
  email: string;
  firmId: string;
  runId: string;
}

/**
 * The checkout side of a provider adapter (the half that may run server-side with secret keys).
 * Webhook verification/normalization lives in each adapter's `server.ts` and is wired per-route.
 */
export interface PaymentCheckoutAdapter {
  /** True once this provider has the config it needs to open a checkout. */
  configured(): boolean;
  createSubscriptionCheckout(input: SubscriptionCheckoutInput): Promise<CheckoutDirective>;
  createPackageCheckout(input: PackageCheckoutInput): Promise<CheckoutDirective>;
}
