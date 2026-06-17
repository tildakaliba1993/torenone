"use client";

import { useEffect } from "react";

import * as Sentry from "@sentry/nextjs";

import { ErrorState } from "@/components/ui/error-state";

// Error boundaries must be Client Components (Next.js App Router).
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
    Sentry.captureException(error); // no-op unless a DSN is configured (§5.1)
  }, [error]);

  return (
    <main className="mx-auto w-full max-w-4xl px-6 py-10">
      <ErrorState
        title="This page hit a snag"
        message="An unexpected error occurred while loading your data. Please try again."
        onRetry={reset}
      />
    </main>
  );
}
