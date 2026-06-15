import { createClient } from "@supabase/supabase-js";

/**
 * Server-ONLY Supabase admin client (service-role). NEVER import this into a client
 * component — it carries the powerful service-role key. It is used only from server actions
 * for privileged operations (e.g. inviting colleagues via the Auth admin API).
 *
 * Requires SUPABASE_SERVICE_ROLE_KEY (server-only env — never NEXT_PUBLIC). Throws a clear
 * error when unconfigured (local/dev without the key), so callers can degrade gracefully.
 */
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) {
    throw new Error(
      "Admin Supabase client requires NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY " +
        "(server-only). Set them in the web deployment's server environment.",
    );
  }
  return createClient(url, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}
