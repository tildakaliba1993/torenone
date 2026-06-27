"use server";

import { dodoCheckout } from "./providers/dodo/checkout";
import { paddleCheckout } from "./providers/paddle/checkout";
import { PAYMENT_PROVIDER } from "./config";
import type {
  CheckoutDirective,
  PackageCheckoutInput,
  PaymentCheckoutAdapter,
  SubscriptionCheckoutInput,
} from "./types";

/**
 * Provider-neutral checkout entrypoints. Dispatch to the active provider (the `PAYMENT_PROVIDER`
 * switch) and return a `CheckoutDirective` the client carries out via `beginCheckout`. Swapping
 * provider is an env change only — these signatures never change. See docs/PAYMENTS.md.
 */

function activeAdapter(): PaymentCheckoutAdapter {
  return PAYMENT_PROVIDER === "dodo" ? dodoCheckout : paddleCheckout;
}

/** Whether the active provider has the config it needs to open a checkout (server-evaluated). */
export async function isPaymentConfigured(): Promise<boolean> {
  return activeAdapter().configured();
}

export async function createSubscriptionCheckout(
  input: SubscriptionCheckoutInput,
): Promise<CheckoutDirective> {
  return activeAdapter().createSubscriptionCheckout(input);
}

export async function createPackageCheckout(
  input: PackageCheckoutInput,
): Promise<CheckoutDirective> {
  return activeAdapter().createPackageCheckout(input);
}
