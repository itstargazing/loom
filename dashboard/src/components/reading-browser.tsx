"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import { hostnameOf } from "@/lib/format";
import type { Collection, ReadingCompilerEntry } from "@/lib/types";

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

type CompilePreview = {
  title: string;
  markdown: string;
  passages: Array<{
    id: string;
    passage: string;
    heading: string | null;
    sourceUrl: string;
    pageTitle: string;
    dwellMs: number;
  }>;
};

export function ReadingBrowser({
  initialEntries,
  initialCollections,
  collectionsError,
}: {
  initialEntries: ReadingCompilerEntry[];
  initialCollections: Collection[];
  collectionsError: string | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [entries, setEntries] = useState(initialEntries);
  const [collectionFilter, setCollectionFilter] = useState("all");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [order, setOrder] = useState<"source" | "recent">("source");
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [orderedIds, setOrderedIds] = useState<string[]>([]);
  const [preview, setPreview] = useState<CompilePreview | null>(null);
  const [error, setError] = useState<string | null>(collectionsError);
  const [title, setTitle] = useState("Reading compilation");

  useEffect(() => {
    setEntries(initialEntries);
  }, [initialEntries]);

  const sources = useMemo(() => {
    const map = new Map<string, string>();
    for (const entry of entries) {
      const key = entry.sourceUrl || entry.pageTitle || entry.id;
      map.set(key, entry.pageTitle || hostnameOf(entry.sourceUrl) || key);
    }
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [entries]);

  useEffect(() => {
    if (selectedSources.length === 0 && sources.length > 0) {
      setSelectedSources(sources.map(([key]) => key));
    }
  }, [sources, selectedSources.length]);

  const filtered = useMemo(() => {
    const sinceMs = since ? Date.parse(`${since}T00:00:00Z`) : null;
    const untilMs = until ? Date.parse(`${until}T23:59:59Z`) : null;
    return entries.filter((entry) => {
      if (collectionFilter === "unfiled" && entry.collectionId) return false;
      if (
        collectionFilter !== "all" &&
        collectionFilter !== "unfiled" &&
        entry.collectionId !== collectionFilter
      ) {
        return false;
      }
      const sourceKey = entry.sourceUrl || entry.pageTitle || entry.id;
      if (selectedSources.length > 0 && !selectedSources.includes(sourceKey)) {
        return false;
      }
      const seen = Date.parse(entry.lastSeenAt);
      if (sinceMs !== null && !Number.isNaN(sinceMs) && seen < sinceMs) return false;
      if (untilMs !== null && !Number.isNaN(untilMs) && seen > untilMs) return false;
      return true;
    });
  }, [entries, collectionFilter, selectedSources, since, until]);

  useEffect(() => {
    const ids = filtered.map((entry) => entry.id);
    setOrderedIds((current) => {
      const kept = current.filter((id) => ids.includes(id));
      const missing = ids.filter((id) => !kept.includes(id));
      return [...kept, ...missing];
    });
  }, [filtered]);

  const orderedEntries = useMemo(() => {
    const byId = new Map(filtered.map((entry) => [entry.id, entry]));
    return orderedIds
      .map((id) => byId.get(id))
      .filter((entry): entry is ReadingCompilerEntry => Boolean(entry));
  }, [filtered, orderedIds]);

  function refresh() {
    startTransition(() => router.refresh());
  }

  function move(id: string, delta: number) {
    setOrderedIds((current) => {
      const index = current.indexOf(id);
      if (index < 0) return current;
      const next = index + delta;
      if (next < 0 || next >= current.length) return current;
      const copy = [...current];
      const [item] = copy.splice(index, 1);
      copy.splice(next, 0, item);
      return copy;
    });
  }

  function toggleSource(key: string) {
    setSelectedSources((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key],
    );
  }

  async function buildPreview() {
    setError(null);
    const params = new URLSearchParams();
    params.set("order", order);
    params.set("title", title.trim() || "Reading compilation");
    if (collectionFilter === "unfiled") params.set("unfiled", "true");
    if (collectionFilter !== "all" && collectionFilter !== "unfiled") {
      params.set("collection_id", collectionFilter);
    }
    if (since) params.set("since", `${since}T00:00:00Z`);
    if (until) params.set("until", `${until}T23:59:59Z`);
    for (const id of orderedIds) params.append("entry_id", id);
    try {
      const result = await proxy<CompilePreview>(
        `/skills/reading/compile?${params.toString()}`,
      );
      //  Keep only selected sources client-side when multiple URLs are chosen.
      const allowed = new Set(selectedSources);
      const passages = result.passages.filter((passage) => {
        const key = passage.sourceUrl || passage.pageTitle || passage.id;
        return allowed.size === 0 || allowed.has(key);
      });
      setPreview({
        ...result,
        passages,
        markdown: result.markdown,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not compile");
    }
  }

  async function download(format: "md" | "txt" | "pdf") {
    setError(null);
    const params = new URLSearchParams();
    params.set("format", format);
    params.set("order", order);
    params.set("title", title.trim() || "Reading compilation");
    if (collectionFilter === "unfiled") params.set("unfiled", "true");
    if (collectionFilter !== "all" && collectionFilter !== "unfiled") {
      params.set("collection_id", collectionFilter);
    }
    if (since) params.set("since", `${since}T00:00:00Z`);
    if (until) params.set("until", `${until}T23:59:59Z`);
    for (const id of orderedIds) params.append("entry_id", id);
    try {
      const response = await fetch(`/api/proxy/skills/reading/export?${params.toString()}`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string" ? body.detail : `Export failed (${response.status})`,
        );
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download =
        response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] ??
        `reading.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not export");
    }
  }

  async function remove(entry: ReadingCompilerEntry) {
    if (!window.confirm("Delete this passage from the reading compiler?")) return;
    setError(null);
    try {
      await proxy(`/skills/reading/${entry.id}`, { method: "DELETE" });
      setEntries((current) => current.filter((row) => row.id !== entry.id));
      setPreview(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not delete");
    }
  }

  async function fileIn(entry: ReadingCompilerEntry, collectionId: string) {
    setError(null);
    try {
      const updated = await proxy<ReadingCompilerEntry>(`/skills/reading/${entry.id}`, {
        method: "PATCH",
        body: JSON.stringify({ collectionId: collectionId || null }),
      });
      setEntries((current) =>
        current.map((row) => (row.id === updated.id ? updated : row)),
      );
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not file entry");
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      <div className="grid gap-md lg:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          Collection
          <select
            className="loom-input"
            value={collectionFilter}
            onChange={(event) => setCollectionFilter(event.target.value)}
          >
            <option value="all">All</option>
            <option value="unfiled">Unfiled</option>
            {initialCollections.map((collection) => (
              <option key={collection.id} value={collection.id}>
                {collection.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          From
          <input
            type="date"
            className="loom-input"
            value={since}
            onChange={(event) => setSince(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          To
          <input
            type="date"
            className="loom-input"
            value={until}
            onChange={(event) => setUntil(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-text-secondary">
          Order
          <select
            className="loom-input"
            value={order}
            onChange={(event) => setOrder(event.target.value as "source" | "recent")}
          >
            <option value="source">Source order</option>
            <option value="recent">Most recent</option>
          </select>
        </label>
      </div>

      <label className="flex flex-col gap-1 text-xs text-text-secondary">
        Document title
        <input
          className="loom-input"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
      </label>

      <div className="flex flex-col gap-sm">
        <p className="font-mono text-xs text-text-secondary">Sources</p>
        <div className="flex flex-wrap gap-sm">
          {sources.map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={
                selectedSources.includes(key)
                  ? "loom-btn"
                  : "loom-btn loom-btn-secondary"
              }
              onClick={() => toggleSource(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-sm">
        <button
          type="button"
          className="loom-btn"
          disabled={pending || orderedEntries.length === 0}
          onClick={() => void buildPreview()}
        >
          Compile preview
        </button>
        <button
          type="button"
          className="loom-btn loom-btn-secondary"
          disabled={orderedEntries.length === 0}
          onClick={() => void download("md")}
        >
          Markdown
        </button>
        <button
          type="button"
          className="loom-btn loom-btn-secondary"
          disabled={orderedEntries.length === 0}
          onClick={() => void download("txt")}
        >
          Plain text
        </button>
        <button
          type="button"
          className="loom-btn loom-btn-secondary"
          disabled={orderedEntries.length === 0}
          onClick={() => void download("pdf")}
        >
          PDF
        </button>
      </div>

      {error ? <p className="text-sm text-error">{error}</p> : null}

      <div className="grid gap-lg lg:grid-cols-2">
        <div className="flex flex-col gap-md">
          <h2 className="text-sm font-medium">Passages ({orderedEntries.length})</h2>
          {orderedEntries.length === 0 ? (
            <EmptyState>
              No dwell passages match these filters. Open a long article with scroll
              dwell capture enabled, or widen the time range.
            </EmptyState>
          ) : (
            <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
              {orderedEntries.map((entry, index) => (
                <li key={entry.id} className="flex flex-col gap-sm py-md">
                  <div className="flex items-start justify-between gap-md">
                    <div className="min-w-0">
                      <p className="text-xs text-text-secondary">
                        {entry.pageTitle || hostnameOf(entry.sourceUrl)}
                        {entry.heading ? ` · ${entry.heading}` : ""}
                        {` · ${Math.round(entry.dwellMs / 1000)}s`}
                        {" · "}
                        <RelativeTime iso={entry.lastSeenAt} />
                      </p>
                      <p className="mt-1 text-sm text-text-primary">{entry.passage}</p>
                    </div>
                    <div className="flex shrink-0 flex-col gap-1">
                      <button
                        type="button"
                        className="text-xs underline"
                        disabled={index === 0}
                        onClick={() => move(entry.id, -1)}
                      >
                        Up
                      </button>
                      <button
                        type="button"
                        className="text-xs underline"
                        disabled={index === orderedEntries.length - 1}
                        onClick={() => move(entry.id, 1)}
                      >
                        Down
                      </button>
                      <button
                        type="button"
                        className="text-xs text-error underline"
                        onClick={() => void remove(entry)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <label className="flex items-center gap-sm text-xs text-text-secondary">
                    File in
                    <select
                      className="loom-input py-1"
                      value={entry.collectionId ?? ""}
                      onChange={(event) => void fileIn(entry, event.target.value)}
                    >
                      <option value="">Unfiled</option>
                      {initialCollections.map((collection) => (
                        <option key={collection.id} value={collection.id}>
                          {collection.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-col gap-md">
          <h2 className="text-sm font-medium">Compiled document</h2>
          {preview ? (
            <pre className="loom-card max-h-[40rem] overflow-auto whitespace-pre-wrap p-md text-sm text-text-primary">
              {preview.markdown}
            </pre>
          ) : (
            <EmptyState>
              Choose sources and click Compile preview to assemble a linear reading
              document from the passages you actually dwelled on.
            </EmptyState>
          )}
        </div>
      </div>
    </div>
  );
}
