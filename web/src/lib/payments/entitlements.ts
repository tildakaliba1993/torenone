import type { createAdminClient } from "@/lib/supabase/admin";

import type { NormalizedEvent } from "./types";

/**
 * The single place that writes entitlement state — shared by every provider's webhook route.
 * Subscription events update the firm's plan/status; PAYG purchases insert a per-run credit.
 * Writes go through the service-role admin client (RLS-bypassing) supplied by the route.
 *
 * Columns are provider-neutral (`payment_*`); `payment_provider` records which MoR owns the row.
 */

type Admin = ReturnType<typeof createAdminClient>;

export async function applyNormalizedEvent(admin: Admin, event: NormalizedEvent): Promise<void> {
  if (!event) return; // ignored / unmappable event — no-op

  if (event.kind === "subscription") {
    await admin
      .from("firms")
      .update({
        plan: "firm",
        payment_provider: event.provider,
        payment_customer_id: event.customerId,
        payment_subscription_id: event.subscriptionId,
        subscription_status: event.status,
        subscription_current_period_end: event.currentPeriodEnd,
      })
      .eq("id", event.firmId);
    return;
  }

  // PAYG: one paid calc package unlocks that run's PDF forever (re-downloads stay free).
  await admin.from("design_credits").upsert(
    {
      run_id: event.runId,
      firm_id: event.firmId,
      payment_provider: event.provider,
      payment_transaction_id: event.transactionId,
    },
    { onConflict: "run_id", ignoreDuplicates: true },
  );
}
