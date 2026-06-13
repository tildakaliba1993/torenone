import Link from "next/link";
import { redirect } from "next/navigation";

import { signOut } from "@/app/auth/actions";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/server";

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
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-3">
          <div className="flex items-center gap-6">
            <Link
              href="/projects"
              className="font-mono text-xs tracking-widest text-accent uppercase"
            >
              TorenOne
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
              <Button type="submit" variant="ghost" size="sm">
                Sign out
              </Button>
            </form>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
