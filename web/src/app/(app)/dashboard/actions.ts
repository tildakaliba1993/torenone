"use server";

import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

/**
 * Invite a colleague into the caller's firm (Task §8.2). Owner-only.
 *
 * The caller's `firm_id` and `role` are resolved server-side from the session (never trusted
 * from the client). The invite is sent via the Supabase Auth admin API (service-role,
 * server-only) with `firm_id` in the user metadata — the handle_new_user() trigger (Task 5.2)
 * reads it and joins the invitee to the firm as an `engineer` when they accept.
 */
export async function inviteColleague(input: { email: string }): Promise<{ error?: string }> {
  const email = input.email?.trim().toLowerCase();
  if (!email) return { error: "Email is required" };

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return { error: "You are not signed in." };

  // RLS-scoped read of the caller's own profile.
  const { data: profile } = await supabase
    .from("profiles")
    .select("role, firm_id")
    .eq("id", user.id)
    .single();
  if (!profile?.firm_id) return { error: "No firm is linked to your account." };
  if (profile.role !== "owner") {
    return { error: "Only the firm owner can invite colleagues." };
  }

  let admin;
  try {
    admin = createAdminClient();
  } catch {
    return { error: "Invites are not configured on this deployment." };
  }

  // redirectTo is omitted → Supabase uses the project's configured Site URL; the invitee
  // confirms via /auth/confirm and sets a password at /reset-password.
  const { error } = await admin.auth.admin.inviteUserByEmail(email, {
    data: { firm_id: profile.firm_id },
  });
  if (error) return { error: error.message };
  return {};
}
