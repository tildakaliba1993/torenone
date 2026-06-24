import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { InviteColleagueForm } from "@/components/auth/invite-colleague-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";

import { inviteColleague } from "./actions";

export const metadata: Metadata = { title: "Account" };

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
    <main className="flex w-full flex-col gap-8">
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

      {role === "owner" ? (
        <Card>
          <CardHeader>
            <CardTitle>Invite a colleague</CardTitle>
            <CardDescription>
              Invite another engineer into {firmName}. They’ll join with the “engineer” role.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <InviteColleagueForm invite={inviteColleague} />
          </CardContent>
        </Card>
      ) : null}
    </main>
  );
}
