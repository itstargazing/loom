"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import { hostnameOf } from "@/lib/format";
import type {
  DocumentDiffEvent,
  WatchedSet,
  WatchedSetDetail,
} from "@/lib/types";

async function proxyJson<T>(path: string, init?: RequestInit): Promise<T> {
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

function DiffBlock({ event }: { event: DocumentDiffEvent }) {
  if (!event.unifiedDiff) {
    return (
      <p className="text-xs text-text-secondary">{event.changeSummary}</p>
    );
  }
  return (
    <pre className="loom-glass loom-sheen-mid max-h-80 overflow-auto whitespace-pre-wrap p-md text-xs loom-mono">
      {event.unifiedDiff}
    </pre>
  );
}

export function LiveDocDiffBrowser({
  initialSets,
}: {
  initialSets: WatchedSet[];
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [sets, setSets] = useState(initialSets);
  const [selectedId, setSelectedId] = useState<string | null>(
    initialSets[0]?.id ?? null,
  );
  const [detail, setDetail] = useState<WatchedSetDetail | null>(null);
  const [newSetName, setNewSetName] = useState("");
  const [docUrl, setDocUrl] = useState("");
  const [docLabel, setDocLabel] = useState("");
  const [docText, setDocText] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSets(initialSets);
  }, [initialSets]);

  function refresh() {
    startTransition(() => router.refresh());
  }

  async function loadDetail(setId: string) {
    setError(null);
    try {
      const next = await proxyJson<WatchedSetDetail>(
        `/skills/live-doc-diff/sets/${setId}`,
      );
      setDetail(next);
      setSelectedId(setId);
      if (next.unreadMeaningful > 0) {
        const marked = await proxyJson<WatchedSet>(
          `/skills/live-doc-diff/sets/${setId}/viewed`,
          { method: "POST" },
        );
        setSets((current) =>
          current.map((row) => (row.id === setId ? { ...row, ...marked } : row)),
        );
        setDetail((current) =>
          current
            ? {
                ...current,
                unreadMeaningful: 0,
                lastViewedAt: marked.lastViewedAt,
                events: current.events.map((event) => ({
                  ...event,
                  viewedAt: event.viewedAt ?? marked.lastViewedAt,
                })),
              }
            : current,
        );
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not load set");
    }
  }

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const next = await proxyJson<WatchedSetDetail>(
          `/skills/live-doc-diff/sets/${selectedId}`,
        );
        if (cancelled) return;
        setDetail(next);
        setError(null);
        if (next.unreadMeaningful > 0) {
          const marked = await proxyJson<WatchedSet>(
            `/skills/live-doc-diff/sets/${selectedId}/viewed`,
            { method: "POST" },
          );
          if (cancelled) return;
          setSets((current) =>
            current.map((row) =>
              row.id === selectedId ? { ...row, ...marked } : row,
            ),
          );
          setDetail((current) =>
            current
              ? {
                  ...current,
                  unreadMeaningful: 0,
                  lastViewedAt: marked.lastViewedAt,
                  events: current.events.map((event) => ({
                    ...event,
                    viewedAt: event.viewedAt ?? marked.lastViewedAt,
                  })),
                }
              : current,
          );
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Could not load set");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function createSet() {
    setError(null);
    try {
      const created = await proxyJson<WatchedSet>("/skills/live-doc-diff/sets", {
        method: "POST",
        body: JSON.stringify({ name: newSetName }),
      });
      setNewSetName("");
      setSets((current) => [created, ...current]);
      setSelectedId(created.id);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create set");
    }
  }

  async function removeSet(setId: string) {
    if (!window.confirm("Delete this watched set and its history?")) return;
    setError(null);
    try {
      await proxyJson(`/skills/live-doc-diff/sets/${setId}`, { method: "DELETE" });
      setSets((current) => current.filter((row) => row.id !== setId));
      if (selectedId === setId) {
        setSelectedId(null);
        setDetail(null);
      }
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete set");
    }
  }

  async function removeDocument(documentId: string, label: string) {
    if (!window.confirm(`Remove “${label}” from this set?`)) return;
    setError(null);
    try {
      await proxyJson(`/skills/live-doc-diff/documents/${documentId}`, {
        method: "DELETE",
      });
      if (selectedId) await loadDetail(selectedId);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not remove document");
    }
  }

  async function addDocument() {
    if (!selectedId) return;
    setError(null);
    try {
      await proxyJson(`/skills/live-doc-diff/sets/${selectedId}/documents`, {
        method: "POST",
        body: JSON.stringify({
          sourceUrl: docUrl,
          label: docLabel || undefined,
          text: docText || undefined,
        }),
      });
      setDocUrl("");
      setDocLabel("");
      setDocText("");
      await loadDetail(selectedId);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not add document");
    }
  }

  async function scan() {
    if (!selectedId) return;
    setError(null);
    try {
      const next = await proxyJson<WatchedSetDetail>(
        `/skills/live-doc-diff/sets/${selectedId}/scan`,
        { method: "POST" },
      );
      setDetail(next);
      setSets((current) =>
        current.map((row) =>
          row.id === selectedId
            ? {
                ...row,
                unreadMeaningful: next.unreadMeaningful,
                latestEventAt: next.latestEventAt,
                documents: next.documents,
              }
            : row,
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Scan failed");
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      {error ? <p className="text-sm text-error">{error}</p> : null}

      <div className="flex flex-wrap items-end gap-sm">
        <label className="flex min-w-[14rem] flex-1 flex-col gap-1 text-xs text-text-secondary">
          New watched set
          <input
            className="loom-input"
            value={newSetName}
            onChange={(event) => setNewSetName(event.target.value)}
            placeholder="Group assignment drafts"
          />
        </label>
        <button
          type="button"
          className="loom-btn"
          disabled={pending || !newSetName.trim()}
          onClick={() => void createSet()}
        >
          Create set
        </button>
      </div>

      {sets.length === 0 ? (
        <EmptyState>
          No watched sets yet. Create one, then add two document URLs (or paste draft
          text) and scan for divergence.
        </EmptyState>
      ) : (
        <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
          {sets.map((row) => (
            <li key={row.id} className="flex items-start justify-between gap-md py-md">
              <button
                type="button"
                className="min-w-0 text-left text-sm"
                onClick={() => setSelectedId(row.id)}
              >
                <span className="font-medium">{row.name}</span>
                <span className="mt-1 block text-xs text-text-secondary">
                  {`${row.documents.length} document${row.documents.length === 1 ? "" : "s"}`}
                  {row.unreadMeaningful > 0
                    ? ` · ${row.unreadMeaningful} unread`
                    : ""}
                  {row.latestEventAt ? (
                    <>
                      {" · "}
                      <RelativeTime iso={row.latestEventAt} />
                    </>
                  ) : null}
                </span>
              </button>
              <button
                type="button"
                className="text-xs underline"
                onClick={() => void removeSet(row.id)}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {detail ? (
        <div className="flex flex-col gap-lg">
          <div className="flex flex-wrap items-center justify-between gap-sm">
            <h2 className="text-base font-medium">{detail.name}</h2>
            <button
              type="button"
              className="loom-btn loom-btn-secondary"
              onClick={() => void scan()}
            >
              Scan now
            </button>
          </div>

          <ul className="flex flex-col gap-sm text-sm">
            {detail.documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-start justify-between gap-md rounded-sm border border-border-soft px-md py-sm"
              >
                <div className="min-w-0">
                  <span className="font-medium">{doc.label}</span>
                  <span className="mt-1 block text-xs text-text-secondary">
                    {hostnameOf(doc.sourceUrl)} ·{" "}
                    {`${doc.snapshotCount} snapshot${doc.snapshotCount === 1 ? "" : "s"}`}
                    {doc.latestSnapshotAt ? (
                      <>
                        {" · "}
                        <RelativeTime iso={doc.latestSnapshotAt} />
                      </>
                    ) : (
                      " · no snapshot yet"
                    )}
                  </span>
                </div>
                <button
                  type="button"
                  className="shrink-0 text-xs underline"
                  onClick={() => void removeDocument(doc.id, doc.label)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>

          <div className="loom-glass loom-sheen-tr flex flex-col gap-sm p-md">
            <p className="text-xs text-text-secondary">
              Add a document by URL. Optional text seeds the first snapshot when no
              capture exists yet (Google Docs OAuth is not required).
            </p>
            <input
              className="loom-input"
              value={docUrl}
              onChange={(event) => setDocUrl(event.target.value)}
              placeholder="https://docs.google.com/document/d/…"
            />
            <input
              className="loom-input"
              value={docLabel}
              onChange={(event) => setDocLabel(event.target.value)}
              placeholder="Label (optional)"
            />
            <textarea
              className="loom-input min-h-[6rem]"
              value={docText}
              onChange={(event) => setDocText(event.target.value)}
              placeholder="Optional draft text for the first snapshot"
            />
            <button
              type="button"
              className="loom-btn self-start"
              disabled={!docUrl.trim()}
              onClick={() => void addDocument()}
            >
              Add document
            </button>
          </div>

          <div className="flex flex-col gap-md">
            <h3 className="font-mono text-xs font-medium text-text-secondary">
              Divergence timeline
            </h3>
            {detail.events.length === 0 ? (
              <EmptyState>
                No diffs yet. Add at least two documents with text, then Scan now.
              </EmptyState>
            ) : (
              detail.events.map((event) => (
                <article
                  key={event.id}
                  className="loom-glass loom-sheen-mid flex flex-col gap-sm p-md"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-sm">
                    <p className="text-sm font-medium">
                      {event.leftLabel} ↔ {event.rightLabel}
                      {event.isMeaningful ? (
                        <span className="ml-2 text-xs font-normal text-warning">
                          Meaningful
                        </span>
                      ) : (
                        <span className="ml-2 text-xs font-normal text-text-secondary">
                          Trivial
                        </span>
                      )}
                    </p>
                    <span className="text-xs text-text-secondary">
                      <RelativeTime iso={event.detectedAt} />
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary">{event.changeSummary}</p>
                  <DiffBlock event={event} />
                </article>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
