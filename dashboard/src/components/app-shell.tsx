"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AskBar } from "@/components/ask-bar";
import { NotificationBell } from "@/components/notification-bell";
import { Sidebar } from "@/components/sidebar";

function isAuthRoute(pathname: string): boolean {
  return pathname.startsWith("/sign-in") || pathname.startsWith("/sign-up");
}

/** Dashboard chrome. Auth pages render children only (no sidebar). */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (isAuthRoute(pathname)) {
    return <>{children}</>;
  }

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar />
      <main className="min-w-0 flex-1 px-md py-xl sm:px-xl">
        <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-lg">
          <div className="loom-glass loom-glass-nested loom-sheen-tr flex items-center gap-md px-md py-sm">
            <AskBar />
            <NotificationBell />
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
