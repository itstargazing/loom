"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  ExtensionUnavailableError,
  triggerSync,
} from "@/lib/extension";

export function SyncCta() {
  const router = useRouter();
  const [label, setLabel] = useState("Sync now");
  const [busy, setBusy] = useState(false);

  async function onSync() {
    setBusy(true);
    try {
      const outcome = await triggerSync();
      if (outcome.status === "synced") {
        setLabel(`Sent ${outcome.sent}`);
        router.refresh();
      } else if (outcome.status === "empty") {
        setLabel("Queue empty");
      } else if (outcome.status === "busy") {
        setLabel("Already syncing");
      } else if (outcome.status === "backoff") {
        setLabel("Backing off");
      } else {
        setLabel("Sync failed");
      }
    } catch (error) {
      setLabel(
        error instanceof ExtensionUnavailableError
          ? "Load the extension"
          : "Sync failed",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      className="loom-btn"
      disabled={busy}
      onClick={() => void onSync()}
    >
      {busy ? "Syncing…" : label}
    </button>
  );
}
