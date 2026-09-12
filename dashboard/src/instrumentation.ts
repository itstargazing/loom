/**
 * Optional Sentry. No-op unless SENTRY_DSN / NEXT_PUBLIC_SENTRY_DSN is set.
 * Next.js loads this file automatically when present.
 */
export async function register() {
  const dsn =
    process.env.SENTRY_DSN?.trim() ||
    process.env.NEXT_PUBLIC_SENTRY_DSN?.trim();
  if (!dsn) return;

  const Sentry = await import("@sentry/nextjs");
  Sentry.init({
    dsn,
    environment: process.env.NODE_ENV,
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0"),
    sendDefaultPii: false,
  });
}
