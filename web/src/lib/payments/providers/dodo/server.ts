import crypto from "node:crypto";

import type { NormalizedEvent, SubscriptionStatus } from "../../types";

/**
 * Server-only Dodo Payments helpers — webhook signing secret, Standard Webhooks signature
 * verification, and event normalization into the provider-neutral shape. NEVER import into a
 * client component. See docs/PAYMENTS.md.
 */

export const DODO_WEBHOOK_SECRET = process.env.DODO_WEBHOOK_SECRET ?? "";

export interface DodoSignatureHeaders {
  id: string | null;
  timestamp: string | null;
  signature: string | null;
}

/**
 * Verify a Dodo webhook signature (the Standard Webhooks scheme). The signed content is
 * `"{id}.{timestamp}.{rawBody}"`; the signature is base64 HMAC-SHA256 keyed by the secret
 * (the bytes are base64 after the optional `whsec_` prefix). The `webhook-signature` header is a
 * space-delimited list of `v1,<sig>` entries — we accept if any matches (constant-time compare).
 * Returns false on any malformed/missing input (never throws).
 */
export function verifyDodoSignature(
  rawBody: string,
  headers: DodoSignatureHeaders,
  secret: string = DODO_WEBHOOK_SECRET,
): boolean {
  const { id, timestamp, signature } = headers;
  if (!secret || !id || !timestamp || !signature) return false;

  const keyB64 = secret.startsWith("whsec_") ? secret.slice("whsec_".length) : secret;
  let key: Buffer;
  try {
    key = Buffer.from(keyB64, "base64");
  } catch {
    return false;
  }
  if (key.length === 0) return false;

  const expected = crypto
    .createHmac("sha256", key)
    .update(`${id}.${timestamp}.${rawBody}`)
    .digest();

  const provided = signature.split(" ").map((part) => {
    const comma = part.indexOf(",");
    return comma === -1 ? part : part.slice(comma + 1);
  });

  return provided.some((sig) => {
    let buf: Buffer;
    try {
      buf = Buffer.from(sig, "base64");
    } catch {
      return false;
    }
    return buf.length === expected.length && crypto.timingSafeEqual(buf, expected);
  });
}

/** Subset of the Dodo webhook payload we act on. */
interface DodoEvent {
  type: string;
  data?: {
    subscription_id?: string;
    payment_id?: string;
    status?: string;
    customer?: { customer_id?: string } | null;
    next_billing_date?: string | null;
    metadata?: { firm_id?: string; run_id?: string } | null;
  };
}

/** Dodo subscription status → our canonical enum (firms.subscription_status). */
const STATUS_MAP: Record<string, SubscriptionStatus> = {
  active: "active",
  trialing: "trialing",
  on_hold: "past_due",
  failed: "past_due",
  paused: "paused",
  cancelled: "canceled",
  canceled: "canceled",
  expired: "canceled",
};

/**
 * Normalize a raw Dodo webhook body into the provider-neutral event. Returns null for events we
 * don't act on, unmappable payloads (e.g. missing firm_id in metadata), or invalid JSON.
 */
export function normalizeDodoEvent(rawBody: string): NormalizedEvent {
  let event: DodoEvent;
  try {
    event = JSON.parse(rawBody) as DodoEvent;
  } catch {
    return null;
  }

  const d = event.data ?? {};
  const meta = d.metadata ?? {};

  if (typeof event.type === "string" && event.type.startsWith("subscription.")) {
    if (!meta.firm_id || !d.subscription_id) return null;
    return {
      kind: "subscription",
      provider: "dodo",
      firmId: meta.firm_id,
      customerId: d.customer?.customer_id ?? null,
      subscriptionId: d.subscription_id,
      status: d.status ? (STATUS_MAP[d.status] ?? null) : null,
      currentPeriodEnd: d.next_billing_date ?? null,
    };
  }

  // A one-off PAYG payment carries the design it unlocks. Subscription renewals also emit
  // payment.succeeded but without a run_id — those are handled by the subscription events.
  if (event.type === "payment.succeeded") {
    if (!meta.firm_id || !meta.run_id || !d.payment_id) return null;
    return {
      kind: "package",
      provider: "dodo",
      firmId: meta.firm_id,
      runId: meta.run_id,
      transactionId: d.payment_id,
    };
  }

  return null;
}
