"use server";

import { createClient } from "@/lib/supabase/server";

export type ReportUrlResult =
  | { url: string }
  | { needsPayment: true; email: string; firmId: string }
  | { error: string };

/**
 * Entitlement-gated calc-package download. Mints a short-lived signed URL only when the firm
 * may download `runId`'s package — an active/trialing Firm subscription, a live complimentary
 * window, or a paid PAYG credit (`public.firm_can_download`). Otherwise returns `needsPayment`
 * so the client can open the PAYG checkout for that design.
 *
 * Resolves the storage path server-side (never trusts a client-passed path). If the billing
 * migration isn't applied yet the RPC errors and we **fail open** (don't block downloads), so
 * the app keeps working until billing is activated.
 */
export async function getEntitledReportUrl(runId: string): Promise<ReportUrlResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "Your session has expired — please sign in again." };

  // RLS scopes this to the caller's firm.
  const { data: report } = await supabase
    .from("reports")
    .select("storage_path")
    .eq("run_id", runId)
    .maybeSingle();
  const storagePath = (report as { storage_path?: string } | null)?.storage_path;
  if (!storagePath) return { error: "No calc package found for this design." };

  const { data: allowed, error: rpcError } = await supabase.rpc("firm_can_download", {
    p_run_id: runId,
  });
  if (!rpcError && allowed === false) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("firm_id")
      .eq("id", user.id)
      .maybeSingle();
    return {
      needsPayment: true,
      email: user.email ?? "",
      firmId: (profile as { firm_id?: string } | null)?.firm_id ?? "",
    };
  }

  const objectPath = storagePath.replace(/^reports\//, "");
  const { data, error } = await supabase.storage.from("reports").createSignedUrl(objectPath, 60);
  if (error || !data?.signedUrl) return { error: "Could not generate a download link." };
  return { url: data.signedUrl };
}
