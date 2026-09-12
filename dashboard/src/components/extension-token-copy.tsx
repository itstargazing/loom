"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";

/**
 * Lets a signed-in user copy a short-lived Clerk JWT for the Chrome extension
 * options page. Prefer a Clerk JWT template named "loom" with a longer TTL.
 */
export function ExtensionTokenCopy() {
  const { getToken, isSignedIn } = useAuth();
  const [status, setStatus] = useState<string | null>(null);

  if (!isSignedIn) return null;

  async function copy(): Promise<void> {
    setStatus(null);
    try {
      const token =
        (await getToken({ template: "loom" })) ?? (await getToken());
      if (!token) {
        setStatus("No token available. Sign in again.");
        return;
      }
      await navigator.clipboard.writeText(token);
      setStatus(
        "Copied. Paste it into the extension Options page. Session tokens expire quickly — create a Clerk JWT template named “loom” for a longer-lived extension token.",
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not copy token");
    }
  }

  return (
    <div className="loom-glass loom-sheen-mid flex flex-col gap-sm p-md">
      <h2 className="font-mono text-xs font-medium text-text-secondary">
        Extension token
      </h2>
      <p className="text-sm text-text-secondary">
        The Chrome extension needs your bearer token in Options. Copy it here,
        then paste under LOOM → Configure API &amp; token.
      </p>
      <button type="button" className="loom-btn self-start" onClick={() => void copy()}>
        Copy session JWT
      </button>
      {status ? <p className="text-xs text-text-secondary">{status}</p> : null}
    </div>
  );
}
