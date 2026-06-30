"use server";

import { revalidatePath } from "next/cache";

import { type ReportMetadata } from "@/lib/api/service";
import { createClient } from "@/lib/supabase/server";

/**
 * Save the project's document/cover metadata (client, engineer, etc.). Every calc package
 * generated for this project then inherits it. Empty/blank values are normalised to null, and
 * an all-blank metadata clears the column. RLS scopes the update to the caller's firm.
 */
export async function updateProjectReportMetadata(input: {
  projectId: string;
  metadata: ReportMetadata;
}): Promise<{ error?: string }> {
  const m = input.metadata;
  const cleaned: ReportMetadata = {
    project_name: m.project_name?.trim() || null,
    client: m.client?.trim() || null,
    project_number: m.project_number?.trim() || null,
    site_address: m.site_address?.trim() || null,
    engineer_name: m.engineer_name?.trim() || null,
    engineer_reg_no: m.engineer_reg_no?.trim() || null,
    revision: m.revision?.trim() || null,
  };
  const hasAny = Object.values(cleaned).some((v) => v);
  const supabase = await createClient();
  const { error } = await supabase
    .from("projects")
    .update({ report_metadata: hasAny ? cleaned : null })
    .eq("id", input.projectId);
  if (error) return { error: error.message };

  revalidatePath(`/projects/${input.projectId}`);
  return {};
}

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
