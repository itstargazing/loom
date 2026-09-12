import { auth } from "@clerk/nextjs/server";
import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { isClerkConfigured } from "@/lib/auth-mode";

/**
 * Authenticated dashboard chrome. Sign-in / sign-up live outside this group.
 */
export default async function AppLayout({ children }: { children: ReactNode }) {
  if (isClerkConfigured()) {
    await auth.protect();
  }
  return <AppShell>{children}</AppShell>;
}
