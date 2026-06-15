"use client";

import { useState } from "react";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

const schema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
});
type Values = z.infer<typeof schema>;

export function ForgotPasswordForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(null);
    const supabase = createClient();
    // The recovery email links to /auth/confirm (verifies the token + sets the session),
    // which then forwards to /reset-password where the user sets a new password.
    const { error } = await supabase.auth.resetPasswordForEmail(values.email, {
      redirectTo: `${window.location.origin}/auth/confirm?next=/reset-password`,
    });
    if (error) {
      setFormError(error.message);
      return;
    }
    setSent(true);
  }

  if (sent) {
    return (
      <div
        role="status"
        className="rounded-md border border-border bg-surface p-4 text-sm text-muted"
      >
        If an account exists for that email, a password-reset link is on its way. Check your
        inbox, then{" "}
        <a className="text-accent hover:underline" href="/login">
          return to sign in
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
        {formError ? (
          <p role="alert" className="text-sm font-medium text-danger">
            {formError}
          </p>
        ) : null}
        <Button type="submit" className="mt-2" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Sending…" : "Send reset link"}
        </Button>
      </form>
    </Form>
  );
}
