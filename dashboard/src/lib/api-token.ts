import { auth } from "@clerk/nextjs/server";

import { allowStubApiToken, isClerkServerConfigured } from "@/lib/auth-mode";

/**
 * Bearer token for the LOOM FastAPI backend.
 * Clerk session JWT when signed in; LOOM_API_TOKEN only in local stub mode.
 */
export async function resolveApiBearerToken(): Promise<string> {
  if (isClerkServerConfigured()) {
    const session = await auth();
    if (!session.userId) {
      throw new Error("Not signed in");
    }
    const token = await session.getToken();
    if (!token) {
      throw new Error("Clerk session has no JWT. Sign in again.");
    }
    return token;
  }

  if (!allowStubApiToken()) {
    throw new Error(
      "Clerk keys are required for this deploy. Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY.",
    );
  }

  return process.env.LOOM_API_TOKEN ?? "loom-dev-token";
}
