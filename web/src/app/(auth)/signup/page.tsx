import type { Metadata } from "next";
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

const PERKS = [
  "Describe a frame → stamp-ready SANS calc package in minutes",
  "Deterministic engine — every number cited to a clause",
  "Free to start · you stay the authoritative engineer",
];

export const metadata: Metadata = {
  title: "Create your account",
  description:
    "Create a free TorenOne firm account and start designing code-checked SANS steel portal frames in minutes.",
  alternates: { canonical: "/signup" },
};

export default async function SignupPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (user) redirect("/projects");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Create your firm account</CardTitle>
        <CardDescription>Start designing code-checked steel portal frames.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <ul className="flex flex-col gap-2">
          {PERKS.map((p) => (
            <li key={p} className="text-muted flex items-start gap-2 text-sm">
              <span className="text-accent mt-0.5 shrink-0">✓</span>
              <span>{p}</span>
            </li>
          ))}
        </ul>
        <SignupForm />
        <p className="text-muted text-sm">
          Already have an account?{" "}
          <Link className="text-accent hover:underline" href="/login">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
