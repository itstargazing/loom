import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { isClerkConfigured } from "@/lib/auth-mode";

/**
 * clerkMiddleware() only attaches the session. Auth gates live on resources
 * (see app/(app)/layout.tsx and the API proxy) — not path matchers here.
 *
 * Do not call clerkMiddleware() when Clerk keys are absent (local stub mode);
 * it validates the publishable key at construction time.
 */
const middleware = isClerkConfigured()
  ? clerkMiddleware()
  : function passthrough(_request: NextRequest) {
      return NextResponse.next();
    };

export default middleware;

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
