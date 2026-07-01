import Link from "next/link";
import { Suspense } from "react";

import { signOut } from "@/app/auth/actions";
import { Logo } from "@/components/brand/logo";
import { RouteTransition } from "@/components/app/route-transition";
import { NavLink } from "@/components/ui/nav-link";
import { Skeleton } from "@/components/ui/skeleton";
import { SubmitButton } from "@/components/ui/submit-button";
import { APP_GUTTER } from "@/lib/layout";
import { createClient } from "@/lib/supabase/server";

import type { Metadata } from "next";

// Authenticated app surface — keep it out of search indexes (private, per-firm data).
export const metadata: Metadata = {
  title: { default: "Projects", template: "%s · TorenOne" },
  robots: { index: false, follow: false },
};

/**
 * The firm name in the header. Rendered inside a Suspense boundary so its Supabase lookup never
 * blocks the shell or the page content — the nav paints instantly and the name streams in.
 */
async function FirmName() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;
  const { data: profile } = await supabase
    .from("profiles")
    .select("firms(name)")
    .eq("id", user.id)
    .single();
  const firmName = (profile?.firms as { name?: string } | null)?.name ?? "TorenOne";
  return <span className="text-muted hidden text-sm sm:inline">{firmName}</span>;
}

/**
 * Shared shell for authenticated app routes: top nav + sign out. Auth is enforced upstream by the
 * proxy middleware (it validates the session and redirects unauthenticated requests to /login), so
 * this layout renders immediately without its own blocking auth round-trip.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-border border-b">
        <div className={`${APP_GUTTER} flex items-center justify-between gap-4 py-3`}>
          <div className="flex items-center gap-6">
            <Link
              href="/projects"
              className="text-foreground flex items-center transition-opacity hover:opacity-80"
            >
              <Logo title="TorenOne — projects" className="h-6 w-auto" />
            </Link>
            <nav className="flex items-center gap-4 text-sm">
              <NavLink href="/projects" active>
                Projects
              </NavLink>
              <NavLink href="/dashboard">Account</NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <Suspense fallback={<Skeleton className="hidden h-4 w-24 sm:block" />}>
              <FirmName />
            </Suspense>
            <form action={signOut}>
              <SubmitButton variant="ghost" size="sm">
                Sign out
              </SubmitButton>
            </form>
          </div>
        </div>
      </header>
      <div className={`${APP_GUTTER} flex-1 py-10`}>
        <RouteTransition>{children}</RouteTransition>
      </div>
    </div>
  );
}
