"use client";

import { useEffect } from "react";

import * as Sentry from "@sentry/nextjs";

// Top-level error boundary for errors in the root layout (Next.js App Router). Reports to
// Sentry when a DSN is configured (no-op otherwise) and renders a minimal fallback.
export default function GlobalError({
  error,
}: {
  error: Error & { digest?: string };
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <main style={{ maxWidth: 480, margin: "10vh auto", padding: "0 1.5rem", fontFamily: "sans-serif" }}>
          <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Something went wrong</h1>
          <p style={{ marginTop: ".5rem", color: "#6b7280" }}>
            An unexpected error occurred. Please reload the page.
          </p>
        </main>
      </body>
    </html>
  );
}
