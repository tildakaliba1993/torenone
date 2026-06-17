import * as Sentry from "@sentry/nextjs";

/**
 * Server/edge error tracking (Production-Readiness §5.1, web half).
 *
 * Initialised only when a DSN is set — a no-op locally, in CI and in tests, exactly
 * like the service-side Sentry. No PII is sent. Set SENTRY_DSN (or NEXT_PUBLIC_SENTRY_DSN)
 * in the deployment to activate.
 */
export async function register() {
  const dsn = process.env.SENTRY_DSN ?? process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return;
  if (process.env.NEXT_RUNTIME === "nodejs" || process.env.NEXT_RUNTIME === "edge") {
    Sentry.init({
      dsn,
      environment: process.env.SENTRY_ENVIRONMENT ?? "production",
      tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0"),
      sendDefaultPii: false,
    });
  }
}

// Captures errors thrown in React Server Components / route handlers (Next instrumentation).
export const onRequestError = Sentry.captureRequestError;
