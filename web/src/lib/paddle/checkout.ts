"use client";

import { PADDLE_CLIENT_TOKEN, PADDLE_ENV, PADDLE_PILOT_DISCOUNT_ID, PADDLE_PRICES } from "./config";

/** Minimal typing of the Paddle.js v2 surface we use (no `any`). */
interface CheckoutItem {
  priceId: string;
  quantity: number;
}
interface CheckoutOpenOptions {
  items: CheckoutItem[];
  customer?: { email?: string };
  customData?: Record<string, string>;
  discountId?: string;
  settings?: { displayMode?: "overlay" | "inline"; successUrl?: string };
}
interface Paddle {
  Environment: { set(env: string): void };
  Initialize(opts: { token: string }): void;
  Checkout: { open(opts: CheckoutOpenOptions): void };
}

declare global {
  interface Window {
    Paddle?: Paddle;
  }
}

let paddlePromise: Promise<Paddle> | null = null;

/** Load + initialise Paddle.js once (idempotent). */
function loadPaddle(): Promise<Paddle> {
  if (typeof window !== "undefined" && window.Paddle) return Promise.resolve(window.Paddle);
  if (paddlePromise) return paddlePromise;

  paddlePromise = new Promise<Paddle>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.paddle.com/paddle/v2/paddle.js";
    script.async = true;
    script.onload = () => {
      const paddle = window.Paddle;
      if (!paddle) {
        reject(new Error("Paddle.js loaded but window.Paddle is missing"));
        return;
      }
      if (PADDLE_ENV === "sandbox") paddle.Environment.set("sandbox");
      paddle.Initialize({ token: PADDLE_CLIENT_TOKEN });
      resolve(paddle);
    };
    script.onerror = () => reject(new Error("Failed to load Paddle.js"));
    document.head.appendChild(script);
  });
  return paddlePromise;
}

/**
 * Open the Firm subscription checkout — always the standard R1,650/mo price (no Paddle trial:
 * pilot firms get their free month as a no-credit-card complimentary grant, not a card-upfront
 * trial). Pilot firms get the recurring discount pre-applied (→ R999/mo for 12 cycles, never a
 * typed coupon). `firm_id` rides in customData so the webhook can map the subscription to the firm.
 */
export async function openFirmSubscriptionCheckout(opts: {
  email: string;
  firmId: string;
  pilot: boolean;
}): Promise<void> {
  const paddle = await loadPaddle();
  paddle.Checkout.open({
    items: [{ priceId: PADDLE_PRICES.firmMonthly, quantity: 1 }],
    customer: { email: opts.email },
    customData: { firm_id: opts.firmId },
    discountId: opts.pilot && PADDLE_PILOT_DISCOUNT_ID ? PADDLE_PILOT_DISCOUNT_ID : undefined,
  });
}

/**
 * Open the pay-as-you-go checkout for a single calc package (R250). `run_id` rides in
 * customData so the webhook unlocks exactly that design.
 */
export async function openCalcPackageCheckout(opts: {
  email: string;
  firmId: string;
  runId: string;
}): Promise<void> {
  const paddle = await loadPaddle();
  paddle.Checkout.open({
    items: [{ priceId: PADDLE_PRICES.calcPackage, quantity: 1 }],
    customer: { email: opts.email },
    customData: { firm_id: opts.firmId, run_id: opts.runId },
  });
}
