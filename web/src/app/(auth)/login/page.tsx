import { Suspense } from "react";

import Link from "next/link";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/auth/login-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user) redirect("/projects");

  const { error } = await searchParams;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Welcome back</CardTitle>
        <CardDescription>Sign in to your firm&rsquo;s workspace.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {error === "confirm" ? (
          <p
            role="alert"
            className="border-warning/40 bg-warning/10 text-warning rounded-md border px-3 py-2 text-sm"
          >
            That link has expired or was already used. Sign in below, or request a new reset link.
          </p>
        ) : null}
        <Suspense>
          <LoginForm />
        </Suspense>
        <div className="flex flex-col gap-1 text-sm">
          <Link className="text-accent hover:underline" href="/forgot-password">
            Forgot your password?
          </Link>
          <p className="text-muted">
            New here?{" "}
            <Link className="text-accent hover:underline" href="/signup">
              Create a firm account
            </Link>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
