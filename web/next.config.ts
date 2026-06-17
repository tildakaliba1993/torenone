import type { NextConfig } from "next";

import { cspHeader } from "./src/lib/security/csp";

// Baseline security headers applied to every route. These are the safe, content-agnostic
// hardening headers that cannot break app functionality (clickjacking, MIME-sniffing,
// referrer leakage, and powerful-feature lockdown).
//
// The Content-Security-Policy (§7.4) is derived from the per-environment Supabase +
// service URLs and is sent **Report-Only** by default — it surfaces violations without
// breaking the app. Set CSP_ENFORCE=true (after a verification pass) to enforce it.
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "X-DNS-Prefetch-Control", value: "off" },
  cspHeader({
    supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
    serviceUrl: process.env.NEXT_PUBLIC_ENGINEERING_SERVICE_URL,
    enforce: process.env.CSP_ENFORCE === "true",
  }),
];

const nextConfig: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
