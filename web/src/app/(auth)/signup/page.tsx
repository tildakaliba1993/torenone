import Link from "next/link";
import { redirect } from "next/navigation";

import { SignupForm } from "@/components/auth/signup-form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { createClient } from "@/lib/supabase/server";

export default async function SignupPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user) redirect("/projects");

  return (
    <Card>
      <CardHeader>
        <span className="font-mono text-xs tracking-widest text-accent uppercase">TorenOne</span>
        <CardTitle>Create your firm account</CardTitle>
        <CardDescription>Start designing code-checked steel frames.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <SignupForm />
        <p className="text-sm text-muted">
          Already have an account?{" "}
          <Link className="text-accent hover:underline" href="/login">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
