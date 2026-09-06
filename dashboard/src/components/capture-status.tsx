"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { formatCount, formatRelative } from "@/lib/format";
import {
  ExtensionUnavailableError,
  detectExtension,
  getSyncStatus,
  triggerSync,
  type BridgeSyncOutcome,
  type BridgeSyncStatus,
} from "@/lib/extension";

import { Badge } from "./skill-table";
import type { Tone } from "@/lib/skills";

type State =
  | { phase: "checking" }
  | { phase: "absent" }
  | { phase: "ready"; status: BridgeSyncStatus }
  | { phase: "error"; message: string };

function describeOutcome(outcome: BridgeSyncOutcome): string {
  switch (outcome.status) {
    case "synced":
      return `Sent ${formatCount(outcome.sent)} event${outcome.sent === 1 ? "" : "s"}.`;
    case "empty":
      return "Queue was already empty.";
    case "busy":
      return "A sync is already running.";
    case "backoff":
      return `Backing off for ${Math.ceil(outcome.retryInMs / 1000)}s.`;
    case "failed":
      return `Failed: ${outcome.error}`;
  }
}

function queueTone(status: BridgeSyncStatus): Tone {
  if (status.lastError) return "error";
  if (status.queued > 0) return "warning";
  return "success";
}

function queueLabel(status: BridgeSyncStatus): string {
  if (status.queued === 0) return "Queue empty";
  return `${formatCount(status.queued)} queued`;
}

/**
 * Live view of the extension's outbound queue, plus the manual sync trigger.
 *
 * A successful sync refreshes the server components on the page so the new
 * events show up without a reload — though classification runs asynchronously,
 * so the very newest events may take another moment to appear.
 */
export function CaptureStatus() {
  const router = useRouter();
  const [state, setState] = useState<State>({ phase: "checking" });
  const [message, setMessage] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [refreshing, startRefresh] = useTransition();

  const refreshStatus = useCallback(async () => {
    try {
      setState({ phase: "ready", status: await getSyncStatus() });
    } catch (error) {
      if (error instanceof ExtensionUnavailableError) {
        setState({ phase: "absent" });
        return;
      }
      setState({
        phase: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      if (!(await detectExtension())) {
        if (!cancelled) setState({ phase: "absent" });
        return;
      }
      if (!cancelled) await refreshStatus();
    })();

    const timer = window.setInterval(() => void refreshStatus(), 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [refreshStatus]);

  async function onSync() {
    setSyncing(true);
    setMessage(null);
    try {
      const outcome = await triggerSync();
      setMessage(describeOutcome(outcome));
      await refreshStatus();
      if (outcome.status === "synced") startRefresh(() => router.refresh());
    } catch (error) {
      setMessage(
        error instanceof ExtensionUnavailableError
          ? "Extension did not respond."
          : error instanceof Error
            ? error.message
            : "Sync failed.",
      );
    } finally {
      setSyncing(false);
    }
  }

  if (state.phase === "checking") {
    return (
      <p className="text-sm text-text-secondary">Looking for the LOOM extension…</p>
    );
  }

  if (state.phase === "absent") {
    return (
      <div className="loom-card p-md">
        <p className="text-sm font-medium">Extension not detected</p>
        <p className="mt-1 text-sm text-text-secondary">
          Load the unpacked extension from <span className="loom-mono">extension/dist</span>{" "}
          and reload this page. Captured events sync from there.
        </p>
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <div className="loom-card p-md">
        <p className="text-sm font-medium">Extension reachable, but errored</p>
        <p className="loom-mono mt-1 text-xs text-error">{state.message}</p>
      </div>
    );
  }

  const { status } = state;

  return (
    <div className="loom-card flex flex-col gap-md p-md">
      <div className="flex items-center justify-between gap-md">
        <div className="flex items-center gap-sm">
          <Badge tone={queueTone(status)}>{queueLabel(status)}</Badge>
          <span className="text-xs text-text-secondary">
            {status.lastSyncedAtMs
              ? `Last sync ${formatRelative(new Date(status.lastSyncedAtMs).toISOString())}`
              : "Never synced"}
          </span>
        </div>
        <button
          type="button"
          onClick={() => void onSync()}
          disabled={syncing || refreshing}
          className="loom-btn loom-btn-secondary"
        >
          {syncing ? "Syncing…" : refreshing ? "Refreshing…" : "Sync now"}
        </button>
      </div>

      <dl className="grid grid-cols-2 gap-x-lg gap-y-xs text-xs sm:grid-cols-4">
        <div>
          <dt className="text-text-secondary">Synced</dt>
          <dd className="loom-mono">{formatCount(status.totalSynced)}</dd>
        </div>
        <div>
          <dt className="text-text-secondary">Dropped</dt>
          <dd className="loom-mono">{formatCount(status.totalDropped)}</dd>
        </div>
        <div>
          <dt className="text-text-secondary">Failures</dt>
          <dd className="loom-mono">{formatCount(status.failureCount)}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-text-secondary">Backend</dt>
          <dd className="loom-mono truncate" title={status.apiBaseUrl}>
            {status.apiBaseUrl}
          </dd>
        </div>
      </dl>

      {status.lastError ? (
        <p className="loom-mono text-xs text-error">{status.lastError}</p>
      ) : null}

      {message ? <p className="text-xs text-text-secondary">{message}</p> : null}
    </div>
  );
}
