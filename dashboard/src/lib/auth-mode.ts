/**
 * Dashboard auth mode: Clerk when keys are present, else local stub token.
 * Production / Vercel never falls back to LOOM_API_TOKEN.
 */

/** Safe on client + server — publishable key is public. */
export function isClerkConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());
}

/** Server-only: both keys required to mint/verify session tokens. */
export function isClerkServerConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim() &&
      process.env.CLERK_SECRET_KEY?.trim(),
  );
}

/** True when the static LOOM_API_TOKEN path is allowed (local stub only). */
export function allowStubApiToken(): boolean {
  if (process.env.NODE_ENV === "production" || process.env.VERCEL === "1") {
    return false;
  }
  return !isClerkServerConfigured();
}
