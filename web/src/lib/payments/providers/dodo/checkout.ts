/**
 * Dodo Payments checkout adapter — creates a hosted checkout session server-side (Bearer API
 * key) and returns a `redirect` directive the client navigates to. `firm_id` (and `run_id` for
 * PAYG) ride in `metadata` so the webhook maps the purchase back to the firm/design.
 *
 * SERVER-ONLY (uses DODO_API_KEY). Never import into a client component.
 */

import { SITE_URL } from "@/lib/site";

import type {
  CheckoutDirective,
  PackageCheckoutInput,
  PaymentCheckoutAdapter,
  SubscriptionCheckoutInput,
} from "../../types";
import {
  DODO_API_BASE,
  DODO_API_KEY,
  DODO_PILOT_DISCOUNT_CODE,
  DODO_PRODUCTS,
  dodoConfigured,
} from "./config";

function configured(): boolean {
  return dodoConfigured();
}

/** Where Dodo sends the customer back after checkout (success or cancel). */
function returnUrl(): string {
  return `${SITE_URL}/dashboard?checkout=complete`;
}

interface CheckoutSessionResponse {
  checkout_url?: string;
  url?: string;
  payment_link?: string;
}

async function createCheckout(opts: {
  productId: string;
  email: string;
  customData: Record<string, string>;
  discountCode?: string;
}): Promise<CheckoutDirective> {
  if (!dodoConfigured()) throw new Error("Dodo Payments is not configured in this environment.");

  const res = await fetch(`${DODO_API_BASE}/checkouts`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${DODO_API_KEY}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      product_cart: [{ product_id: opts.productId, quantity: 1 }],
      customer: { email: opts.email },
      metadata: opts.customData,
      return_url: returnUrl(),
      ...(opts.discountCode ? { discount_code: opts.discountCode } : {}),
    }),
  });

  if (!res.ok) {
    throw new Error(`Dodo checkout failed (${res.status})`);
  }

  const json = (await res.json()) as CheckoutSessionResponse;
  const url = json.checkout_url ?? json.url ?? json.payment_link;
  if (!url) throw new Error("Dodo checkout returned no URL");
  return { type: "redirect", url };
}

async function createSubscriptionCheckout(
  input: SubscriptionCheckoutInput,
): Promise<CheckoutDirective> {
  return createCheckout({
    productId: DODO_PRODUCTS.firmMonthly,
    email: input.email,
    customData: { firm_id: input.firmId },
    discountCode: input.pilot && DODO_PILOT_DISCOUNT_CODE ? DODO_PILOT_DISCOUNT_CODE : undefined,
  });
}

async function createPackageCheckout(input: PackageCheckoutInput): Promise<CheckoutDirective> {
  return createCheckout({
    productId: DODO_PRODUCTS.calcPackage,
    email: input.email,
    customData: { firm_id: input.firmId, run_id: input.runId },
  });
}

export const dodoCheckout: PaymentCheckoutAdapter = {
  configured,
  createSubscriptionCheckout,
  createPackageCheckout,
};
