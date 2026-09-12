"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";

/**
 * Copies a Clerk JWT minted from the "loom" JWT template for the extension
 * options page. Requires that template to exist in the Clerk dashboard.
 */
export function ExtensionTokenCopy() {
  const { getToken, isSignedIn } = useAuth();
  const [status, setStatus] = useState<string | null>(null);

  if (!isSignedIn) return null;

  async function copy(): Promise<void> {
    setStatus(null);
    try {
      const token = await getToken({ template: "loom" });
      if (!token) {
        setStatus(
          'No “loom” JWT available. Create a Clerk JWT template named “loom”, then sign in again.',
        );
        return;
      }
      await navigator.clipboard.writeText(token);
      setStatus("Copied. Paste it into the extension Options page.");
    } catch (error) {
      setStatus(
        error instanceof Error
          ? error.message
          : 'Could not copy the “loom” JWT. Check that the Clerk template exists.',
      );
    }
  }

  return (
    <div className="loom-glass loom-sheen-mid flex flex-col gap-sm p-md">
      <h2 className="font-mono text-xs font-medium text-text-secondary">
        Extension token
      </h2>
      <p className="text-sm text-text-secondary">
        Copies a JWT from the Clerk template named{" "}
        <span className="loom-mono">loom</span>. Paste it under LOOM → Configure
        API &amp; token in the extension.
      </p>
      <button type="button" className="loom-btn self-start" onClick={() => void copy()}>
        Copy loom JWT
      </button>
      {status ? <p className="text-xs text-text-secondary">{status}</p> : null}
    </div>
  );
}
