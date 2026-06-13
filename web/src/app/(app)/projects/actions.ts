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
