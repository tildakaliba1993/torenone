import { type NextRequest, NextResponse } from "next/server";

import { type EmailOtpType } from "@supabase/supabase-js";

import { createClient } from "@/lib/supabase/server";

/**
 * Email-confirmation / password-recovery landing (Task 6.2 + 8.1). Supabase sends the
 * user here from confirmation and reset emails. We support BOTH link formats:
 *   • PKCE  — a `?code=` we exchange for a session (the DEFAULT email-template format),
 *   • OTP   — a `?token_hash=&type=` we verify (the customised SSR-template format).
 * Either way we set the session cookie, then redirect to `next` (e.g. /reset-password).
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  const supabase = await createClient();

  // PKCE flow — the format Supabase's default recovery/confirmation links use. Exchanging
  // the code for a session is what makes password reset work without custom email templates.
  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(new URL(next, request.url));
    }
  }

  // OTP flow — used when the email templates are customised to the SSR token_hash format.
  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    if (!error) {
      return NextResponse.redirect(new URL(next, request.url));
    }
  }

  return NextResponse.redirect(new URL("/login?error=confirm", request.url));
}
