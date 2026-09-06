"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import { hostnameOf } from "@/lib/format";
import type { Contradiction } from "@/lib/types";

async function proxy<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/proxy${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body as T;
}

export function ContradictionsBrowser({
  initialEntries,
}: {
  initialEntries: Contradiction[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [showDismissed, setShowDismissed] = useState(false);
  const [entries, setEntries] = useState(initialEntries);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEntries(initialEntries);
  }, [initialEntries]);

  const visible = useMemo(() => {
    if (showDismissed) return entries;
    return entries.filter((entry) => !entry.dismissed);
  }, [entries, showDismissed]);

  function refresh() {
    startTransition(() => router.refresh());
  }

  async function setDismissed(entry: Contradiction, dismissed: boolean) {
    setError(null);
    try {
      const updated = await proxy<Contradiction>(`/skills/contradictions/${entry.id}`, {
        method: "PATCH",
        body: JSON.stringify({ dismissed }),
      });
      setEntries((current) =>
        current.map((row) => (row.id === updated.id ? updated : row)),
      );
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not update");
    }
  }

  async function remove(entry: Contradiction) {
    if (!window.confirm("Delete this flagged contradiction?")) return;
    setError(null);
    try {
      await proxy(`/skills/contradictions/${entry.id}`, { method: "DELETE" });
      setEntries((current) => current.filter((row) => row.id !== entry.id));
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete");
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex flex-wrap items-center gap-md">
        <button
          type="button"
          className={showDismissed ? "loom-btn" : "loom-btn loom-btn-secondary"}
          onClick={() => setShowDismissed((value) => !value)}
        >
          {showDismissed ? "Hiding dismissed" : "Show dismissed"}
        </button>
        <p className="text-xs text-text-secondary">
          {visible.length} {visible.length === 1 ? "pair" : "pairs"}
        </p>
      </div>

      {error ? <p className="text-sm text-error">{error}</p> : null}

      {visible.length === 0 ? (
        <EmptyState>
          {initialEntries.length === 0
            ? "No conflicting claims yet. As you capture checkable figures from different sources, the watcher pairs them here."
            : "All flagged contradictions are dismissed. Toggle “Show dismissed” to review them."}
        </EmptyState>
      ) : (
        <ul className="flex flex-col gap-lg">
          {visible.map((entry) => (
            <li
              key={entry.id}
              className={[
                "loom-card flex flex-col gap-md p-md",
                entry.dismissed ? "opacity-60" : "",
              ].join(" ")}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-md">
                <p className="font-mono text-xs text-text-secondary">
                  {entry.topic}
                </p>
                <p className="text-xs text-text-secondary">
                  <RelativeTime iso={entry.createdAt} />
                </p>
              </div>

              <p className="text-sm text-text-primary">{entry.explanation}</p>

              <div className="grid gap-md md:grid-cols-2">
                <ClaimPanel
                  label="Source A"
                  claim={entry.claimA}
                  sourceUrl={entry.sourceAUrl}
                />
                <ClaimPanel
                  label="Source B"
                  claim={entry.claimB}
                  sourceUrl={entry.sourceBUrl}
                />
              </div>

              <div className="flex flex-wrap gap-md">
                {entry.dismissed ? (
                  <button
                    type="button"
                    className="loom-btn loom-btn-secondary"
                    disabled={pending}
                    onClick={() => void setDismissed(entry, false)}
                  >
                    Restore
                  </button>
                ) : (
                  <button
                    type="button"
                    className="loom-btn loom-btn-secondary"
                    disabled={pending}
                    onClick={() => void setDismissed(entry, true)}
                  >
                    Dismiss
                  </button>
                )}
                <button
                  type="button"
                  className="text-xs text-error underline"
                  onClick={() => void remove(entry)}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ClaimPanel({
  label,
  claim,
  sourceUrl,
}: {
  label: string;
  claim: string;
  sourceUrl: string;
}) {
  return (
    <div className="loom-glass loom-sheen-mid flex flex-col gap-sm p-md">
      <p className="font-mono text-xs text-text-secondary">{label}</p>
      <p className="text-sm text-text-primary">“{claim}”</p>
      {sourceUrl ? (
        <a
          href={sourceUrl}
          className="text-xs underline"
          target="_blank"
          rel="noreferrer"
        >
          {hostnameOf(sourceUrl)}
        </a>
      ) : (
        <p className="text-xs text-text-secondary">No source URL</p>
      )}
    </div>
  );
}
