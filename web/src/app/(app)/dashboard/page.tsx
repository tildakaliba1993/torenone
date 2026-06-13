import { redirect } from "next/navigation";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  // The proxy already guards this route; this is a defensive fallback.
  if (!user) redirect("/login");

  // RLS (Task 5.4) scopes this read to the caller's own firm.
  const { data: profile } = await supabase
    .from("profiles")
    .select("role, firm_id, firms(name)")
    .eq("id", user.id)
    .single();

  const firmName = (profile?.firms as { name?: string } | null)?.name ?? "—";
  const role = (profile?.role as string | undefined) ?? "—";

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Account</h1>
        <p className="text-sm text-muted">Signed in as {user.email}</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Your firm</CardTitle>
          <CardDescription>Multi-tenant workspace — data is RLS-scoped to your firm.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col text-sm">
          <div className="flex justify-between border-b border-border py-2">
            <span className="text-muted">Firm</span>
            <span className="font-medium">{firmName}</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-muted">Role</span>
            <span className="font-mono">{role}</span>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
