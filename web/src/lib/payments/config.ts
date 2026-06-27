/**
 * Which payment provider is active. ONE switch: `NEXT_PUBLIC_PAYMENT_PROVIDER`. Flip it (and set
 * that provider's env) to swap Merchant-of-Record without touching code — Paddle today, Dodo
 * Payments while/after Paddle KYB clears. One provider is active at a time. See docs/PAYMENTS.md.
 *
 * Safe on both client and server: it only reads the public provider id (NEXT_PUBLIC). Provider
 * secrets live in the adapters' server-only modules.
 */

import type { PaymentProviderId } from "./types";

export const PAYMENT_PROVIDER: PaymentProviderId =
  process.env.NEXT_PUBLIC_PAYMENT_PROVIDER === "dodo" ? "dodo" : "paddle";
