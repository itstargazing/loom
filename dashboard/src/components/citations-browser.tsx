"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import { Badge } from "@/components/skill-table";
import { apiErrorMessage } from "@/lib/api-error";
import { hostnameOf } from "@/lib/format";
import type { Citation, Collection } from "@/lib/types";

type CitationStyle = "apa" | "mla";

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
    throw new Error(apiErrorMessage(body, `Request failed (${response.status})`));
  }
  return body as T;
}

function formattedOf(entry: Citation, style: CitationStyle): string {
  return entry.formatted?.[style] || entry.formatted?.apa || entry.formatted?.mla || "";
}

export function CitationsBrowser({
  initialCitations,
  initialCollections,
  collectionsError,
}: {
  initialCitations: Citation[];
  initialCollections: Collection[];
  collectionsError: string | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [query, setQuery] = useState("");
  const [collectionFilter, setCollectionFilter] = useState<string>("all");
  const [style, setStyle] = useState<CitationStyle>("apa");
  const [newCollection, setNewCollection] = useState("");
  const [error, setError] = useState<string | null>(collectionsError);
  const [editing, setEditing] = useState<string | null>(null);

  const collectionsById = useMemo(
    () => new Map(initialCollections.map((collection) => [collection.id, collection])),
    [initialCollections],
  );

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return initialCitations.filter((entry) => {
      if (collectionFilter === "unfiled" && entry.collectionId) return false;
      if (
        collectionFilter !== "all" &&
        collectionFilter !== "unfiled" &&
        entry.collectionId !== collectionFilter
      ) {
        return false;
      }
      if (!needle) return true;
      const haystack = [
        entry.quote,
        entry.author,
        entry.workTitle,
        entry.publisher,
        formattedOf(entry, style),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [initialCitations, query, collectionFilter, style]);

  const grouped = useMemo(() => {
    const groups = new Map<string, { name: string; entries: Citation[] }>();
    for (const entry of visible) {
      const key = entry.collectionId ?? "unfiled";
      const name = entry.collectionId
        ? (collectionsById.get(entry.collectionId)?.name ?? "Unknown collection")
        : "Unfiled";
      const group = groups.get(key) ?? { name, entries: [] };
      group.entries.push(entry);
      groups.set(key, group);
    }
    return [...groups.entries()].sort(([aKey, a], [bKey, b]) => {
      if (aKey === "unfiled") return 1;
      if (bKey === "unfiled") return -1;
      return a.name.localeCompare(b.name);
    });
  }, [visible, collectionsById]);

  function refresh() {
    startTransition(() => router.refresh());
  }

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong");
    }
  }

  async function createCollection() {
    const name = newCollection.trim();
    if (!name) return;
    await run(async () => {
      await proxy("/collections", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      setNewCollection("");
    });
  }

  async function removeCollection() {
    if (collectionFilter === "all" || collectionFilter === "unfiled") return;
    const name = collectionsById.get(collectionFilter)?.name ?? "this collection";
    if (
      !window.confirm(
        `Delete “${name}”? Citations stay and become unfiled.`,
      )
    ) {
      return;
    }
    await run(async () => {
      await proxy(`/collections/${collectionFilter}`, { method: "DELETE" });
      setCollectionFilter("all");
    });
  }

  async function exportBibliography(format: "txt" | "md") {
    setError(null);
    const params = new URLSearchParams({ style, format });
    if (collectionFilter === "unfiled") params.set("unfiled", "true");
    else if (collectionFilter !== "all") params.set("collection_id", collectionFilter);

    try {
      const response = await fetch(`/api/proxy/skills/citations/export?${params}`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(apiErrorMessage(body, `Export failed (${response.status})`));
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition");
      const match = disposition?.match(/filename="([^"]+)"/);
      const filename = match?.[1] ?? `citations-${style}.${format}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not export");
    }
  }

  const exportLabel =
    collectionFilter === "all"
      ? "all citations"
      : collectionFilter === "unfiled"
        ? "unfiled citations"
        : collectionsById.get(collectionFilter)?.name ?? "this collection";

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex flex-wrap items-end gap-md">
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1">
          <span className="font-mono text-xs text-text-secondary">
            Search
          </span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Quote, author, work, or citation"
            className="loom-input"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="font-mono text-xs text-text-secondary">
            Collection
          </span>
          <select
            value={collectionFilter}
            onChange={(event) => setCollectionFilter(event.target.value)}
            className="loom-input"
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

        <label className="flex flex-col gap-1">
          <span className="font-mono text-xs text-text-secondary">
            Style
          </span>
          <select
            value={style}
            onChange={(event) => setStyle(event.target.value as CitationStyle)}
            className="loom-input"
          >
            <option value="apa">APA</option>
            <option value="mla">MLA</option>
          </select>
        </label>

        <form
          className="flex flex-col gap-1"
          onSubmit={(event) => {
            event.preventDefault();
            void createCollection();
          }}
        >
          <span className="font-mono text-xs text-text-secondary">
            New collection
          </span>
          <div className="flex gap-sm">
            <input
              type="text"
              value={newCollection}
              onChange={(event) => setNewCollection(event.target.value)}
              placeholder="e.g. Thesis reading"
              className="loom-input"
            />
            <button type="submit" className="loom-btn" disabled={pending || !newCollection.trim()}>
              Add
            </button>
          </div>
        </form>

        {collectionFilter !== "all" && collectionFilter !== "unfiled" ? (
          <button
            type="button"
            className="text-xs text-error underline"
            disabled={pending}
            onClick={() => void removeCollection()}
          >
            Delete collection
          </button>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-sm">
        <span className="text-xs text-text-secondary">
          Export {exportLabel} as {style.toUpperCase()}
        </span>
        <button
          type="button"
          className="loom-btn loom-btn-secondary"
          onClick={() => void exportBibliography("txt")}
          disabled={visible.length === 0}
        >
          Plain text
        </button>
        <button
          type="button"
          className="loom-btn loom-btn-secondary"
          onClick={() => void exportBibliography("md")}
          disabled={visible.length === 0}
        >
          Markdown
        </button>
      </div>

      {error ? <p className="text-sm text-error">{error}</p> : null}

      {visible.length === 0 ? (
        <EmptyState>
          {initialCitations.length === 0
            ? "No citations yet. Copy a claim from a paper or article while browsing; LOOM files it here once it is classified."
            : "No citations match this search or collection."}
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-xl">
          {grouped.map(([key, group]) => (
            <section key={key} className="flex flex-col gap-md">
              <h2 className="loom-mono font-mono text-xs text-text-secondary">
                {group.name}
                <span className="ml-sm text-text-faint">
                  {group.entries.length}
                </span>
              </h2>
              <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
                {group.entries.map((entry) => (
                  <CitationRow
                    key={`${entry.id}-${entry.lastSeenAt}-${entry.collectionId ?? ""}`}
                    entry={entry}
                    style={style}
                    collections={initialCollections}
                    editing={editing === entry.id}
                    busy={pending}
                    onEdit={() => setEditing(entry.id)}
                    onCancelEdit={() => setEditing(null)}
                    onSaved={() => {
                      setEditing(null);
                      refresh();
                    }}
                    onError={setError}
                    onChanged={refresh}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function CitationRow({
  entry,
  style,
  collections,
  editing,
  busy,
  onEdit,
  onCancelEdit,
  onSaved,
  onError,
  onChanged,
}: {
  entry: Citation;
  style: CitationStyle;
  collections: Collection[];
  editing: boolean;
  busy: boolean;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSaved: () => void;
  onError: (message: string | null) => void;
  onChanged: () => void;
}) {
  const [author, setAuthor] = useState(entry.author ?? "");
  const [workTitle, setWorkTitle] = useState(entry.workTitle ?? "");
  const [publisher, setPublisher] = useState(entry.publisher ?? "");
  const [publishedDate, setPublishedDate] = useState(entry.publishedDate ?? "");
  const citation = formattedOf(entry, style);

  async function save() {
    onError(null);
    try {
      await proxy(`/skills/citations/${entry.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          author: author.trim() || null,
          workTitle: workTitle.trim() || null,
          publisher: publisher.trim() || null,
          publishedDate: publishedDate.trim() || null,
        }),
      });
      onSaved();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not save");
    }
  }

  async function remove() {
    if (!window.confirm("Delete this citation?")) return;
    onError(null);
    try {
      await proxy(`/skills/citations/${entry.id}`, { method: "DELETE" });
      onChanged();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not delete");
    }
  }

  async function fileIn(collectionId: string) {
    onError(null);
    try {
      await proxy(`/skills/citations/${entry.id}`, {
        method: "PATCH",
        body: JSON.stringify({ collectionId: collectionId || null }),
      });
      onChanged();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not move");
    }
  }

  return (
    <li className="py-md">
      {editing ? (
        <form
          className="flex flex-col gap-sm"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <p className="text-sm text-text-primary">“{entry.quote}”</p>
          <input
            value={author}
            onChange={(event) => setAuthor(event.target.value)}
            className="loom-input"
            placeholder="Author"
            aria-label="Author"
          />
          <input
            value={workTitle}
            onChange={(event) => setWorkTitle(event.target.value)}
            className="loom-input"
            placeholder="Work title"
            aria-label="Work title"
          />
          <div className="flex flex-wrap gap-sm">
            <input
              value={publisher}
              onChange={(event) => setPublisher(event.target.value)}
              className="loom-input flex-1"
              placeholder="Publisher"
              aria-label="Publisher"
            />
            <input
              value={publishedDate}
              onChange={(event) => setPublishedDate(event.target.value)}
              className="loom-input w-40"
              placeholder="Published date"
              aria-label="Published date"
            />
          </div>
          <div className="flex gap-sm">
            <button type="submit" className="loom-btn" disabled={busy}>
              Save
            </button>
            <button type="button" className="loom-btn loom-btn-secondary" onClick={onCancelEdit}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <>
          <div className="flex items-start justify-between gap-md">
            <div className="min-w-0">
              <p className="text-sm text-text-primary">“{entry.quote}”</p>
              {citation ? (
                <p className="mt-2 text-sm text-text-secondary">{citation}</p>
              ) : null}
              <p className="mt-2 text-xs text-text-secondary">
                {entry.pageTitle || hostnameOf(entry.sourceUrl)}
                {entry.timesSeen > 1 ? ` · seen ${entry.timesSeen} times` : ""}
                {entry.lastSeenAt ? (
                  <>
                    {" · "}
                    <RelativeTime iso={entry.lastSeenAt} />
                  </>
                ) : null}
              </p>
            </div>
            <div className="flex shrink-0 gap-sm">
              <button type="button" className="text-xs text-text-secondary underline" onClick={onEdit}>
                Correct metadata
              </button>
              <button type="button" className="text-xs text-error underline" onClick={() => void remove()}>
                Delete
              </button>
            </div>
          </div>

          <div className="mt-sm flex flex-wrap items-center gap-md">
            <label className="flex items-center gap-sm text-xs text-text-secondary">
              File in
              <select
                value={entry.collectionId ?? ""}
                onChange={(event) => void fileIn(event.target.value)}
                className="loom-input py-1"
                disabled={busy}
              >
                <option value="">Unfiled</option>
                {collections.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>
            {entry.confidence < 0.5 ? <Badge tone="warning">Low confidence</Badge> : null}
          </div>
        </>
      )}
    </li>
  );
}
