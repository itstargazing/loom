/**
 * Optional Sentry. No-op unless SENTRY_DSN / NEXT_PUBLIC_SENTRY_DSN is set
 * and `@sentry/nextjs` is installed (`npm i @sentry/nextjs`).
 *
 * Next.js loads this file automatically when present.
 */
// @ts-nocheck — @sentry/nextjs is optional until you install it for production.
export async function register() {
  const dsn =
    process.env.SENTRY_DSN?.trim() ||
    process.env.NEXT_PUBLIC_SENTRY_DSN?.trim();
  if (!dsn) return;

  try {
    const Sentry = await import("@sentry/nextjs");
    Sentry.init({
      dsn,
      environment: process.env.NODE_ENV,
      tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? "0"),
      sendDefaultPii: false,
    });
  } catch {
    console.warn(
      "[loom] Sentry DSN is set but @sentry/nextjs is not installed. " +
        "Run: npm i @sentry/nextjs",
    );
  }
}
