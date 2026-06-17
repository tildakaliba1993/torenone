/**
 * Content-Security-Policy builder (Production-Readiness §7.4).
 *
 * The `connect-src` must allow the Supabase project (REST + Realtime websocket) and the
 * engineering service, which are per-environment — so the policy is derived from the
 * public env vars at build time. By default the header is sent as **Report-Only**
 * (`Content-Security-Policy-Report-Only`), which surfaces violations without breaking the
 * app; set `CSP_ENFORCE=true` to switch to an enforcing `Content-Security-Policy` once a
 * verification pass confirms nothing legitimate is blocked.
 */

/** Turn an `https://…` origin into its `wss://…` form (Supabase Realtime). */
function toWebSocket(origin: string): string {
  return origin.replace(/^http/, "ws");
}

function originOf(url: string | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

export function buildCsp(env: {
  supabaseUrl?: string;
  serviceUrl?: string;
}): string {
  const supabase = originOf(env.supabaseUrl);
  const service = originOf(env.serviceUrl);

  const connect = new Set<string>(["'self'"]);
  if (supabase) {
    connect.add(supabase);
    connect.add(toWebSocket(supabase)); // Realtime websocket
  }
  if (service) connect.add(service);

  // 'unsafe-inline' is included for script/style because Next + Tailwind inject inline
  // content without a nonce; keeping it means flipping to enforce won't immediately break
  // the app. Tighten with nonces in a later hardening pass.
  const directives: Record<string, string[]> = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-inline'"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:", "blob:"],
    "font-src": ["'self'", "data:"],
    "connect-src": [...connect],
    "frame-ancestors": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "object-src": ["'none'"],
  };

  return Object.entries(directives)
    .map(([k, v]) => `${k} ${v.join(" ")}`)
    .join("; ");
}

/** The CSP header (report-only unless `CSP_ENFORCE=true`). */
export function cspHeader(env: {
  supabaseUrl?: string;
  serviceUrl?: string;
  enforce?: boolean;
}): { key: string; value: string } {
  return {
    key: env.enforce ? "Content-Security-Policy" : "Content-Security-Policy-Report-Only",
    value: buildCsp(env),
  };
}
