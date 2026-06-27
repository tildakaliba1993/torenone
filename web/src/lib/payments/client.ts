"use client";

import type { CheckoutDirective } from "./types";

/**
 * Client-side checkout dispatcher. Given a `CheckoutDirective` from the payments server action,
 * it either redirects to a hosted checkout (Dodo / most MoRs) or opens the Paddle.js overlay.
 * The UI never imports a specific provider — only this and `lib/payments/actions`.
 */

/** Minimal typing of the Paddle.js v2 surface we use (no `any`). */
interface PaddleCheckoutItem {
  priceId: string;
  quantity: number;
}
interface PaddleCheckoutOpenOptions {
  items: PaddleCheckoutItem[];
  customer?: { email?: string };
  customData?: Record<string, string>;
  discountId?: string;
}
interface Paddle {
  Environment: { set(env: string): void };
  Initialize(opts: { token: string }): void;
  Checkout: { open(opts: PaddleCheckoutOpenOptions): void };
}

declare global {
  interface Window {
    Paddle?: Paddle;
  }
}

let paddlePromise: Promise<Paddle> | null = null;

/** Load + initialise Paddle.js once (idempotent). */
function loadPaddle(token: string, env: "sandbox" | "production"): Promise<Paddle> {
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
      if (env === "sandbox") paddle.Environment.set("sandbox");
      paddle.Initialize({ token });
      resolve(paddle);
    };
    script.onerror = () => reject(new Error("Failed to load Paddle.js"));
    document.head.appendChild(script);
  });
  return paddlePromise;
}

/** Carry out a checkout directive produced by the payments server action. */
export async function beginCheckout(directive: CheckoutDirective): Promise<void> {
  if (directive.type === "redirect") {
    window.location.assign(directive.url);
    return;
  }

  // paddle-overlay
  const paddle = await loadPaddle(directive.clientToken, directive.env);
  paddle.Checkout.open({
    items: [{ priceId: directive.priceId, quantity: 1 }],
    customer: { email: directive.email },
    customData: directive.customData,
    discountId: directive.discountId,
  });
}
