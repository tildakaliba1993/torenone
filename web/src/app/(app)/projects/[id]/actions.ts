"use server";

import { revalidatePath } from "next/cache";

import { createClient } from "@/lib/supabase/server";

/** Rename a design run's label (searchable). RLS scopes the update to the firm. */
export async function renameRun(input: {
  id: string;
  projectId: string;
  label: string;
}): Promise<{ error?: string }> {
  const label = input.label?.trim();
  const supabase = await createClient();
  const { error } = await supabase
    .from("runs")
    .update({ label: label || null })
    .eq("id", input.id);
  if (error) return { error: error.message };

  revalidatePath(`/projects/${input.projectId}`);
  return {};
}

/**
 * Delete a single design run. The DB cascades its `reports` row; we remove the report
 * PDF from Storage first. RLS scopes every step to the caller's firm.
 */
export async function deleteRun(input: {
  id: string;
  projectId: string;
}): Promise<{ error?: string }> {
  const supabase = await createClient();

  const { data: reports } = await supabase
    .from("reports")
    .select("storage_path")
    .eq("run_id", input.id);
  const paths = (reports ?? [])
    .map((r) => (r as { storage_path: string | null }).storage_path)
    .filter((p): p is string => Boolean(p))
    .map((p) => p.replace(/^reports\//, ""));
  if (paths.length > 0) {
    await supabase.storage.from("reports").remove(paths);
  }

  const { error } = await supabase.from("runs").delete().eq("id", input.id);
  if (error) return { error: error.message };

  revalidatePath(`/projects/${input.projectId}`);
  return {};
}
