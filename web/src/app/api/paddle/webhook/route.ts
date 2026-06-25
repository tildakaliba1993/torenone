import { NextResponse } from "next/server";

import { verifyPaddleSignature } from "@/lib/paddle/server";
import { createAdminClient } from "@/lib/supabase/admin";

export const runtime = "nodejs";

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

type Admin = ReturnType<typeof createAdminClient>;

async function handleSubscription(admin: Admin, event: PaddleEvent): Promise<void> {
  const firmId = event.data.custom_data?.firm_id;
  if (!firmId) return; // can't map — ignore (don't make Paddle retry forever)
  await admin
    .from("firms")
    .update({
      plan: "firm",
      paddle_customer_id: event.data.customer_id ?? null,
      paddle_subscription_id: event.data.id,
      subscription_status: event.data.status ?? null,
      subscription_current_period_end: event.data.current_billing_period?.ends_at ?? null,
    })
    .eq("id", firmId);
}

async function handleTransaction(admin: Admin, event: PaddleEvent): Promise<void> {
  // A one-off PAYG purchase carries the design it unlocks. Subscription renewals also emit
  // transaction.completed but without a run_id — those are handled by the subscription events.
  const { firm_id: firmId, run_id: runId } = event.data.custom_data ?? {};
  if (!firmId || !runId) return;
  await admin.from("design_credits").upsert(
    {
      run_id: runId,
      firm_id: firmId,
      paddle_transaction_id: event.data.id,
    },
    { onConflict: "run_id", ignoreDuplicates: true },
  );
}

export async function POST(req: Request): Promise<NextResponse> {
  const raw = await req.text();
  if (!verifyPaddleSignature(raw, req.headers.get("paddle-signature"))) {
    return NextResponse.json({ error: "invalid signature" }, { status: 401 });
  }

  let event: PaddleEvent;
  try {
    event = JSON.parse(raw) as PaddleEvent;
  } catch {
    return NextResponse.json({ error: "invalid JSON" }, { status: 400 });
  }

  let admin: Admin;
  try {
    admin = createAdminClient();
  } catch {
    return NextResponse.json({ error: "billing not configured" }, { status: 503 });
  }

  try {
    if (SUBSCRIPTION_EVENTS.has(event.event_type)) {
      await handleSubscription(admin, event);
    } else if (event.event_type === "transaction.completed") {
      await handleTransaction(admin, event);
    }
    // Unhandled event types are acknowledged (200) so Paddle doesn't retry them.
  } catch {
    // Transient failure — 500 makes Paddle retry with backoff.
    return NextResponse.json({ error: "processing failed" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
