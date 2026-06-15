"use client";

import { useState } from "react";

import { useRouter } from "next/navigation";

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
import { passwordSchema } from "@/lib/auth/password";
import { createClient } from "@/lib/supabase/client";

const schema = z
  .object({
    password: passwordSchema,
    confirm: z.string().min(1, "Please confirm your password"),
  })
  .refine((v) => v.password === v.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });
type Values = z.infer<typeof schema>;

export function ResetPasswordForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(null);
    const supabase = createClient();
    // The recovery link (via /auth/confirm) has already set a session, so updateUser can
    // change the password. If there's no session, Supabase returns a clear error.
    const { error } = await supabase.auth.updateUser({ password: values.password });
    if (error) {
      setFormError(error.message);
      return;
    }
    setDone(true);
  }

  if (done) {
    return (
      <div
        role="status"
        className="rounded-md border border-border bg-surface p-4 text-sm text-muted"
      >
        Your password has been updated.{" "}
        <button
          type="button"
          className="text-accent hover:underline"
          onClick={() => {
            router.push("/projects");
            router.refresh();
          }}
        >
          Continue
        </button>
        .
      </div>
    );
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>New password</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="confirm"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm new password</FormLabel>
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
          {form.formState.isSubmitting ? "Updating…" : "Update password"}
        </Button>
      </form>
    </Form>
  );
}
