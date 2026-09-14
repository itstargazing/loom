"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { isClerkConfigured } from "@/lib/auth-mode";
import {
  ExtensionUnavailableError,
  detectExtension,
  triggerSync,
} from "@/lib/extension";

type TokenGetter = () => Promise<string | null>;

function SyncCtaImpl({ getToken }: { getToken: TokenGetter }) {
  const router = useRouter();
  const [label, setLabel] = useState("Sync now");
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [extensionReady, setExtensionReady] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    void detectExtension().then((ready) => {
      if (cancelled) return;
      setExtensionReady(ready);
      if (!ready) {
        setHint(
          "Extension not detected on this page. Load unpacked from extension/dist, then reload this tab.",
        );
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSync() {
    setBusy(true);
    setHint(null);
    try {
      if (!(await detectExtension())) {
        setExtensionReady(false);
        setLabel("Load the extension");
        setHint(
          "LOOM content script is not on this page. chrome://extensions → Load unpacked → extension/dist, then reload this tab. Hosted dashboards must add this origin under extension Options.",
        );
        return;
      }
      setExtensionReady(true);

      const authToken = (await getToken()) ?? undefined;
      const outcome = await triggerSync(authToken);
      if (outcome.status === "synced") {
        setLabel(`Sent ${outcome.sent}`);
        setHint(null);
        router.refresh();
      } else if (outcome.status === "empty") {
        setLabel("Queue empty");
        setHint("Nothing queued. Capture a highlight first, then sync.");
      } else if (outcome.status === "busy") {
        setLabel("Already syncing");
      } else if (outcome.status === "backoff") {
        setLabel("Backing off");
        setHint(`Retry in about ${Math.ceil(outcome.retryInMs / 1000)}s.`);
      } else if (outcome.status === "failed") {
        setLabel("Sync failed");
        setHint(
          outcome.error.includes("401") || outcome.error.includes("403")
            ? "API rejected the token. Stay signed in on the dashboard, or paste a Clerk JWT in extension Options."
            : outcome.error,
        );
      } else {
        setLabel("Sync failed");
      }
    } catch (error) {
      if (error instanceof ExtensionUnavailableError) {
        setExtensionReady(false);
        setLabel("Load the extension");
        setHint(
          "No reply from the extension bridge. Reload the unpacked extension and this tab.",
        );
      } else {
        setLabel("Sync failed");
        setHint(error instanceof Error ? error.message : "Sync failed");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-xs">
      <button
        type="button"
        className="loom-btn"
        disabled={busy}
        onClick={() => void onSync()}
        title={
          extensionReady === false
            ? "Extension not detected"
            : "Push queued capture events to the API"
        }
      >
        {busy ? "Syncing…" : label}
      </button>
      {hint ? (
        <p className="max-w-sm text-xs text-text-secondary">{hint}</p>
      ) : null}
    </div>
  );
}

function SyncCtaClerk() {
  const { getToken } = useAuth();
  return <SyncCtaImpl getToken={() => getToken()} />;
}

/** Overview Sync now — talks to the extension bridge; uses Clerk JWT when signed in. */
export function SyncCta() {
  if (isClerkConfigured()) return <SyncCtaClerk />;
  return <SyncCtaImpl getToken={async () => null} />;
}
