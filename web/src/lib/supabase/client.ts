import { createBrowserClient } from "@supabase/ssr";

/**
 * Supabase client for browser/client components (Task 6.2). Uses the public
 * anon key — RLS (Task 5.4) enforces per-firm isolation server-side. Cookie
 * handling is automatic; the proxy (src/proxy.ts) refreshes the session.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
