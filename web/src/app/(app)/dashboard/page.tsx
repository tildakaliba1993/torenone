import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { InviteColleagueForm } from "@/components/auth/invite-colleague-form";
import { BillingCard } from "@/components/billing/billing-card";
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

interface FirmBilling {
  name?: string;
  is_founding?: boolean;
  subscription_status?: string | null;
  complimentary_until?: string | null;
}

/** Is the no-card complimentary window still open? (Module-level: request-time, not render.) */
function complimentaryActiveNow(until: string | null | undefined): boolean {
  return until ? new Date(until).getTime() > Date.now() : false;
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ subscribe?: string }>;
}) {
  const { subscribe } = await searchParams;
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
  const firmId = (profile?.firm_id as string | undefined) ?? "";

  // Billing columns are added by the Paddle migration; read them separately and tolerate a
  // missing-column error so the page still works before that migration is applied.
  let firm: FirmBilling | null = null;
  if (firmId) {
    const { data } = await supabase
      .from("firms")
      .select("is_founding, subscription_status, complimentary_until")
      .eq("id", firmId)
      .maybeSingle();
    firm = (data as FirmBilling | null) ?? null;
  }

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

      <BillingCard
        email={user.email ?? ""}
        firmId={firmId}
        isFounding={firm?.is_founding ?? false}
        subscriptionStatus={firm?.subscription_status ?? null}
        complimentaryActive={complimentaryActiveNow(firm?.complimentary_until)}
        complimentaryUntil={firm?.complimentary_until ?? null}
        autoSubscribe={subscribe === "firm"}
      />

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
