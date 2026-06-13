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

export default async function LoginPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user) redirect("/projects");

  return (
    <Card>
      <CardHeader>
        <span className="font-mono text-xs tracking-widest text-accent uppercase">TorenOne</span>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>The AI structural engineer.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <Suspense>
          <LoginForm />
        </Suspense>
        <p className="text-sm text-muted">
          New here?{" "}
          <Link className="text-accent hover:underline" href="/signup">
            Create a firm account
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
