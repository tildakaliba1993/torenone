/**
 * Paddle checkout adapter — builds the `paddle-overlay` directive the client uses to open
 * Paddle.js. Pure (reads only public config), so it runs fine inside the payments server action.
 * The actual overlay is opened by the shared client dispatcher (lib/payments/client.ts).
 */

import type {
  CheckoutDirective,
  PackageCheckoutInput,
  PaymentCheckoutAdapter,
  SubscriptionCheckoutInput,
} from "../../types";
import {
  PADDLE_CLIENT_TOKEN,
  PADDLE_ENV,
  PADDLE_PILOT_DISCOUNT_ID,
  PADDLE_PRICES,
  paddleConfigured,
} from "./config";

function configured(): boolean {
  return paddleConfigured();
}

/**
 * Firm subscription — always the standard R1,650/mo price (no Paddle trial: pilot firms get
 * their free month as a no-credit-card complimentary grant, not a card-upfront trial). Pilot
 * firms get the recurring discount pre-applied (→ R999/mo for 12 cycles, never a typed coupon).
 * `firm_id` rides in customData so the webhook can map the subscription to the firm.
 */
async function createSubscriptionCheckout(
  input: SubscriptionCheckoutInput,
): Promise<CheckoutDirective> {
  return {
    type: "paddle-overlay",
    env: PADDLE_ENV,
    clientToken: PADDLE_CLIENT_TOKEN,
    priceId: PADDLE_PRICES.firmMonthly,
    discountId:
      input.pilot && PADDLE_PILOT_DISCOUNT_ID ? PADDLE_PILOT_DISCOUNT_ID : undefined,
    email: input.email,
    customData: { firm_id: input.firmId },
  };
}

/**
 * Pay-as-you-go for a single calc package (R250). `run_id` rides in customData so the webhook
 * unlocks exactly that design.
 */
async function createPackageCheckout(input: PackageCheckoutInput): Promise<CheckoutDirective> {
  return {
    type: "paddle-overlay",
    env: PADDLE_ENV,
    clientToken: PADDLE_CLIENT_TOKEN,
    priceId: PADDLE_PRICES.calcPackage,
    email: input.email,
    customData: { firm_id: input.firmId, run_id: input.runId },
  };
}

export const paddleCheckout: PaymentCheckoutAdapter = {
  configured,
  createSubscriptionCheckout,
  createPackageCheckout,
};
