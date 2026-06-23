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

const schema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
});
type Values = z.infer<typeof schema>;

export function InviteColleagueForm({
  invite,
}: {
  invite: (input: { email: string }) => Promise<{ error?: string }>;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const [invited, setInvited] = useState<string | null>(null);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(null);
    const { error } = await invite({ email: values.email });
    if (error) {
      setFormError(error);
      return;
    }
    setInvited(values.email);
    form.reset();
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Colleague’s email</FormLabel>
              <FormControl>
                <Input
                  type="email"
                  autoComplete="off"
                  placeholder="colleague@firm.co.za"
                  {...field}
                />
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
        {invited ? (
          <p role="status" className="text-sm text-success">
            Invitation sent to {invited}.
          </p>
        ) : null}
        <Button type="submit" className="mt-1 self-start" loading={form.formState.isSubmitting} disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Sending…" : "Send invite"}
        </Button>
      </form>
    </Form>
  );
}
