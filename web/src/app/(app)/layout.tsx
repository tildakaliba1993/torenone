import Link from "next/link";
import { redirect } from "next/navigation";

import { signOut } from "@/app/auth/actions";
import { Logo } from "@/components/brand/logo";
import { SubmitButton } from "@/components/ui/submit-button";
import { APP_GUTTER } from "@/lib/layout";
import { createClient } from "@/lib/supabase/server";

import type { Metadata } from "next";

// Authenticated app surface — keep it out of search indexes (private, per-firm data).
export const metadata: Metadata = {
  title: { default: "Projects", template: "%s · TorenOne" },
  robots: { index: false, follow: false },
};

/** Shared shell for authenticated app routes (Task 6.3): top nav + sign out. */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("firms(name)")
    .eq("id", user.id)
    .single();
  const firmName = (profile?.firms as { name?: string } | null)?.name ?? "TorenOne";

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-border">
        <div className={`${APP_GUTTER} flex items-center justify-between gap-4 py-3`}>
          <div className="flex items-center gap-6">
            <Link
              href="/projects"
              className="text-foreground flex items-center transition-opacity hover:opacity-80"
            >
              <Logo title="TorenOne — projects" className="h-6 w-auto" />
            </Link>
            <nav className="flex items-center gap-4 text-sm">
              <Link href="/projects" className="text-foreground hover:text-accent">
                Projects
              </Link>
              <Link href="/dashboard" className="text-muted hover:text-accent">
                Account
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted sm:inline">{firmName}</span>
            <form action={signOut}>
              <SubmitButton variant="ghost" size="sm">
                Sign out
              </SubmitButton>
            </form>
          </div>
        </div>
      </header>
      <div className={`${APP_GUTTER} flex-1 py-10`}>{children}</div>
    </div>
  );
}
