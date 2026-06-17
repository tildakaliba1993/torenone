import * as Sentry from "@sentry/nextjs";

/**
 * Browser error tracking (Production-Readiness §5.1, web half). Initialised only when
 * NEXT_PUBLIC_SENTRY_DSN is set — a no-op otherwise (local/dev/CI/tests). No PII.
 */
const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "production",
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0"),
    sendDefaultPii: false,
  });
}
