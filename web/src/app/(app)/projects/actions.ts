"use server";

import { revalidatePath } from "next/cache";

import { createClient } from "@/lib/supabase/server";

/**
 * Create a project in the caller's firm (Task 6.3). `firm_id` and `created_by`
 * are derived server-side from the session — never trusted from the client —
 * and RLS (Task 5.4) independently enforces `firm_id = current_firm_id()`.
 */
export async function createProject(input: { name: string }): Promise<{ error?: string }> {
  const name = input.name?.trim();
  if (!name) return { error: "Project name is required" };

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "You are not signed in." };

  const { data: profile } = await supabase
    .from("profiles")
    .select("firm_id")
    .eq("id", user.id)
    .single();
  if (!profile?.firm_id) return { error: "No firm is linked to your account." };

  const { error } = await supabase
    .from("projects")
    .insert({ name, firm_id: profile.firm_id, created_by: user.id });
  if (error) return { error: error.message };

  revalidatePath("/projects");
  return {};
}

/** Rename a project (RLS scopes the update to the caller's firm). */
export async function renameProject(input: {
  id: string;
  name: string;
}): Promise<{ error?: string }> {
  const name = input.name?.trim();
  if (!name) return { error: "Project name is required" };

  const supabase = await createClient();
  const { error } = await supabase.from("projects").update({ name }).eq("id", input.id);
  if (error) return { error: error.message };

  revalidatePath("/projects");
  revalidatePath(`/projects/${input.id}`);
  return {};
}

/**
 * Delete a project and everything under it. The DB cascades runs + reports rows
 * (FK ON DELETE CASCADE), but the report PDFs in Storage are separate objects, so we
 * remove them first. RLS scopes every step to the caller's firm.
 */
export async function deleteProject(input: { id: string }): Promise<{ error?: string }> {
  const supabase = await createClient();

  // Collect the storage paths of every report under this project, then delete the objects.
  const { data: reports } = await supabase
    .from("reports")
    .select("storage_path, runs!inner(project_id)")
    .eq("runs.project_id", input.id);
  const paths = (reports ?? [])
    .map((r) => (r as { storage_path: string | null }).storage_path)
    .filter((p): p is string => Boolean(p))
    .map((p) => p.replace(/^reports\//, ""));
  if (paths.length > 0) {
    await supabase.storage.from("reports").remove(paths);
  }

  const { error } = await supabase.from("projects").delete().eq("id", input.id);
  if (error) return { error: error.message };

  revalidatePath("/projects");
  return {};
}
