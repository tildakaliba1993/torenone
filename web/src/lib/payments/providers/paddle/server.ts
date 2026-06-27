import crypto from "node:crypto";

import type { NormalizedEvent, SubscriptionStatus } from "../../types";

/**
 * Server-only Paddle helpers — webhook signing secret, signature verification, and event
 * normalization into the provider-neutral shape. NEVER import into a client component.
 * See docs/PAYMENTS.md.
 */

export const PADDLE_WEBHOOK_SECRET = process.env.PADDLE_WEBHOOK_SECRET ?? "";

/**
 * Verify a Paddle (Billing) webhook signature. The `Paddle-Signature` header looks like
 * `ts=1700000000;h1=<hex>`, where `<hex>` is HMAC-SHA256 of `"{ts}:{rawBody}"` keyed by the
 * destination's secret. Returns false on any malformed/missing input (never throws), and uses
 * a constant-time compare to avoid leaking timing information.
 */
export function verifyPaddleSignature(
  rawBody: string,
  signatureHeader: string | null,
  secret: string = PADDLE_WEBHOOK_SECRET,
): boolean {
  if (!secret || !signatureHeader) return false;

  const parts = Object.fromEntries(
    signatureHeader.split(";").map((kv) => {
      const i = kv.indexOf("=");
      return [kv.slice(0, i).trim(), kv.slice(i + 1).trim()];
    }),
  );
  const ts = parts["ts"];
  const h1 = parts["h1"];
  if (!ts || !h1) return false;

  const expected = crypto
    .createHmac("sha256", secret)
    .update(`${ts}:${rawBody}`)
    .digest("hex");

  const a = Buffer.from(expected, "hex");
  const b = Buffer.from(h1, "hex");
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

/** Subset of the Paddle (Billing) webhook payload we act on. */
interface PaddleEvent {
  event_type: string;
  data: {
    id: string;
    customer_id?: string;
    status?: string;
    current_billing_period?: { ends_at?: string } | null;
    custom_data?: { firm_id?: string; run_id?: string } | null;
  };
}

const SUBSCRIPTION_EVENTS = new Set([
  "subscription.created",
  "subscription.updated",
  "subscription.canceled",
  "subscription.activated",
  "subscription.trialing",
]);

const VALID_STATUSES: ReadonlySet<SubscriptionStatus> = new Set<SubscriptionStatus>([
  "trialing",
  "active",
  "past_due",
  "paused",
  "canceled",
]);

function mapStatus(status: string | undefined): SubscriptionStatus | null {
  return status && VALID_STATUSES.has(status as SubscriptionStatus)
    ? (status as SubscriptionStatus)
    : null;
}

/**
 * Normalize a raw Paddle webhook body into the provider-neutral event. Returns null for events
 * we don't act on, unmappable payloads (e.g. missing firm_id), or invalid JSON — callers treat
 * null as a no-op and acknowledge (200) so Paddle doesn't retry forever.
 */
export function normalizePaddleEvent(rawBody: string): NormalizedEvent {
  let event: PaddleEvent;
  try {
    event = JSON.parse(rawBody) as PaddleEvent;
  } catch {
    return null;
  }

  const cd = event.data?.custom_data ?? {};

  if (SUBSCRIPTION_EVENTS.has(event.event_type)) {
    if (!cd.firm_id || !event.data.id) return null;
    return {
      kind: "subscription",
      provider: "paddle",
      firmId: cd.firm_id,
      customerId: event.data.customer_id ?? null,
      subscriptionId: event.data.id,
      status: mapStatus(event.data.status),
      currentPeriodEnd: event.data.current_billing_period?.ends_at ?? null,
    };
  }

  // A one-off PAYG purchase carries the design it unlocks. Subscription renewals also emit
  // transaction.completed but without a run_id — those are handled by the subscription events.
  if (event.event_type === "transaction.completed") {
    if (!cd.firm_id || !cd.run_id || !event.data.id) return null;
    return {
      kind: "package",
      provider: "paddle",
      firmId: cd.firm_id,
      runId: cd.run_id,
      transactionId: event.data.id,
    };
  }

  return null;
}
