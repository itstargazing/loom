"use client";

import { Show, UserButton, useUser } from "@clerk/nextjs";
import Link from "next/link";

/** Signed-in identity + sign-out near Account in the sidebar. */
export function SidebarAuth() {
  const { user, isLoaded } = useUser();
  const label =
    user?.primaryEmailAddress?.emailAddress ??
    user?.username ??
    user?.fullName ??
    "Signed in";

  return (
    <div className="mx-3 flex flex-col gap-sm border-t border-border-soft pt-sm">
      <Show when="signed-in">
        <div className="flex items-center gap-sm">
          <UserButton
            appearance={{
              elements: {
                avatarBox: "h-8 w-8",
              },
            }}
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs text-text-primary">
              {isLoaded ? label : "…"}
            </p>
            <Link
              href="/account"
              className="font-mono text-[10px] text-text-faint hover:text-text-secondary"
            >
              Account
            </Link>
          </div>
        </div>
      </Show>
      <Show when="signed-out">
        <Link href="/sign-in" className="loom-btn loom-btn-secondary text-xs">
          Sign in
        </Link>
      </Show>
    </div>
  );
}
