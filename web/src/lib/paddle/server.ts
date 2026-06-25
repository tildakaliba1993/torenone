import crypto from "node:crypto";

/**
 * Server-only Paddle helpers — the webhook signing secret + signature verification.
 * NEVER import into a client component. See docs/PADDLE.md.
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
