import { NextResponse } from "next/server";

import { applyNormalizedEvent } from "@/lib/payments/entitlements";
import { normalizeDodoEvent, verifyDodoSignature } from "@/lib/payments/providers/dodo/server";
import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";

/**
 * Dodo Payments webhook (Standard Webhooks scheme). Verifies the signature, normalizes the event
 * into the provider-neutral shape, then writes entitlement state via the shared handler. Keep
 * this route even when Paddle is the active provider — Dodo simply won't send traffic.
 */
export async function POST(req: Request): Promise<NextResponse> {
  const raw = await req.text();
  const ok = verifyDodoSignature(raw, {
    id: req.headers.get("webhook-id"),
    timestamp: req.headers.get("webhook-timestamp"),
    signature: req.headers.get("webhook-signature"),
  });
  if (!ok) {
    return NextResponse.json({ error: "invalid signature" }, { status: 401 });
  }

  let admin: ReturnType<typeof createAdminClient>;
  try {
    admin = createAdminClient();
  } catch {
    return NextResponse.json({ error: "billing not configured" }, { status: 503 });
  }

  try {
    // Unmappable / irrelevant events normalize to null and are acknowledged (200).
    await applyNormalizedEvent(admin, normalizeDodoEvent(raw));
  } catch {
    // Transient failure — 500 makes Dodo retry with backoff.
    return NextResponse.json({ error: "processing failed" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
