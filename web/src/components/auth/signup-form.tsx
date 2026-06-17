"use client";

import { useState } from "react";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { passwordSchema } from "@/lib/auth/password";
import { createClient } from "@/lib/supabase/client";

const signupSchema = z.object({
  firmName: z.string().trim().min(1, "Firm name is required"),
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
  password: passwordSchema,
});
type SignupValues = z.infer<typeof signupSchema>;

export function SignupForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const form = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { firmName: "", email: "", password: "" },
  });

  async function onSubmit(values: SignupValues) {
    setFormError(null);
    const supabase = createClient();
    const { data, error } = await supabase.auth.signUp({
      email: values.email,
      password: values.password,
      options: {
        // Read by the handle_new_user() trigger (Task 5.2) to create the firm.
        data: { firm_name: values.firmName },
        emailRedirectTo: `${window.location.origin}/auth/confirm`,
      },
    });
    if (error) {
      setFormError(error.message);
      return;
    }
    if (!data.session) {
      // Email confirmation is enabled — no session until the link is clicked.
      setEmailSent(true);
      return;
    }
    router.push("/projects");
    router.refresh();
  }

  if (emailSent) {
    return (
      <div
        role="status"
        className="rounded-md border border-border bg-surface p-4 text-sm text-muted"
      >
        Check your email to confirm your account, then{" "}
        <a className="text-accent hover:underline" href="/login">
          sign in
        </a>
        .
      </div>
    );
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="firmName"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Firm name</FormLabel>
              <FormControl>
                <Input autoComplete="organization" placeholder="Acme Structural" {...field} />
              </FormControl>
              <FormDescription>Creates a new firm — you’ll be its owner.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" autoComplete="email" placeholder="you@firm.co.za" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {formError ? (
          <p role="alert" className="text-sm font-medium text-danger">
            {formError}
          </p>
        ) : null}
        <Button type="submit" className="mt-2" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Creating account…" : "Create account"}
        </Button>
        <p className="text-subtle text-xs">
          By creating an account you agree to our{" "}
          <Link href="/terms" className="text-accent hover:underline">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="text-accent hover:underline">
            Privacy Policy
          </Link>
          .
        </p>
      </form>
    </Form>
  );
}
