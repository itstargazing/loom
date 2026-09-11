"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/panel";
import { RelativeTime } from "@/components/relative-time";
import { Badge } from "@/components/skill-table";
import { apiErrorMessage } from "@/lib/api-error";
import { hostnameOf } from "@/lib/format";
import type { Collection, GlossaryTerm, Sighting } from "@/lib/types";

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

function letterOf(term: string): string {
  const first = term.trim().charAt(0).toUpperCase();
  return first >= "A" && first <= "Z" ? first : "#";
}

function asSightings(entry: GlossaryTerm): Sighting[] {
  const first: Sighting = {
    sourceUrl: entry.sourceUrl,
    pageTitle: entry.pageTitle,
    seenAt: entry.createdAt,
    contextSnippet: entry.contextSnippet,
  };
  const later = (entry.occurrences ?? []) as Sighting[];
  return [first, ...later];
}

export function GlossaryBrowser({
  initialTerms,
  initialCollections,
  collectionsError,
}: {
  initialTerms: GlossaryTerm[];
  initialCollections: Collection[];
  collectionsError: string | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [query, setQuery] = useState("");
  const [collectionFilter, setCollectionFilter] = useState<string>("all");
  const [newCollection, setNewCollection] = useState("");
  const [error, setError] = useState<string | null>(collectionsError);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);

  const collectionsById = useMemo(
    () => new Map(initialCollections.map((collection) => [collection.id, collection])),
    [initialCollections],
  );

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return initialTerms.filter((entry) => {
      if (collectionFilter === "unfiled" && entry.collectionId) return false;
      if (
        collectionFilter !== "all" &&
        collectionFilter !== "unfiled" &&
        entry.collectionId !== collectionFilter
      ) {
        return false;
      }
      if (!needle) return true;
      return (
        entry.term.toLowerCase().includes(needle) ||
        entry.definition.toLowerCase().includes(needle) ||
        entry.contextSnippet.toLowerCase().includes(needle)
      );
    });
  }, [initialTerms, query, collectionFilter]);

  const grouped = useMemo(() => {
    const groups = new Map<string, GlossaryTerm[]>();
    for (const entry of visible) {
      const letter = letterOf(entry.term);
      const list = groups.get(letter) ?? [];
      list.push(entry);
      groups.set(letter, list);
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [visible]);

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
        `Delete “${name}”? Terms stay in the glossary and become unfiled.`,
      )
    ) {
      return;
    }
    await run(async () => {
      await proxy(`/collections/${collectionFilter}`, { method: "DELETE" });
      setCollectionFilter("all");
    });
  }

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
            placeholder="Term, definition, or context"
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
              placeholder="e.g. CS201"
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

      {error ? <p className="text-sm text-error">{error}</p> : null}

      {visible.length === 0 ? (
        <EmptyState>
          {initialTerms.length === 0
            ? "No terms yet. Highlight an unfamiliar word while browsing; LOOM files it here once it is classified."
            : "No terms match this search or collection."}
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-xl">
          {grouped.map(([letter, entries]) => (
            <section key={letter} className="flex flex-col gap-md">
              <h2 className="loom-mono font-mono text-xs text-text-secondary">
                {letter}
              </h2>
              <ul className="loom-glass loom-sheen-mid flex flex-col divide-y divide-border-soft px-md">
                {entries.map((entry) => (
                  <GlossaryRow
                    key={`${entry.id}-${entry.lastSeenAt}-${entry.collectionId ?? ""}`}
                    entry={entry}
                    collections={initialCollections}
                    collectionName={
                      entry.collectionId
                        ? collectionsById.get(entry.collectionId)?.name ?? null
                        : null
                    }
                    expanded={expanded === entry.id}
                    editing={editing === entry.id}
                    busy={pending}
                    onToggle={() =>
                      setExpanded((current) => (current === entry.id ? null : entry.id))
                    }
                    onEdit={() => setEditing(entry.id)}
                    onCancelEdit={() => setEditing(null)}
                    onSaved={() => {
                      setEditing(null);
                      refresh();
                    }}
                    onError={setError}
                    onDeleted={refresh}
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

function GlossaryRow({
  entry,
  collections,
  collectionName,
  expanded,
  editing,
  busy,
  onToggle,
  onEdit,
  onCancelEdit,
  onSaved,
  onError,
  onDeleted,
}: {
  entry: GlossaryTerm;
  collections: Collection[];
  collectionName: string | null;
  expanded: boolean;
  editing: boolean;
  busy: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSaved: () => void;
  onError: (message: string | null) => void;
  onDeleted: () => void;
}) {
  const [term, setTerm] = useState(entry.term);
  const [definition, setDefinition] = useState(entry.definition);
  const sightings = asSightings(entry);

  async function save() {
    onError(null);
    try {
      await proxy(`/skills/glossary/${entry.id}`, {
        method: "PATCH",
        body: JSON.stringify({ term, definition }),
      });
      onSaved();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not save");
    }
  }

  async function remove() {
    if (!window.confirm(`Delete “${entry.term}” from the glossary?`)) return;
    onError(null);
    try {
      await proxy(`/skills/glossary/${entry.id}`, { method: "DELETE" });
      onDeleted();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not delete");
    }
  }

  async function fileIn(collectionId: string) {
    onError(null);
    try {
      await proxy(`/skills/glossary/${entry.id}`, {
        method: "PATCH",
        body: JSON.stringify({ collectionId: collectionId || null }),
      });
      onDeleted();
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
          <input
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            className="loom-input loom-mono"
            aria-label="Term"
          />
          <textarea
            value={definition}
            onChange={(event) => setDefinition(event.target.value)}
            className="loom-input min-h-[4.5rem]"
            aria-label="Definition"
          />
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
              <p className="loom-mono text-sm font-medium">{entry.term}</p>
              <p className="mt-1 text-sm text-text-primary">{entry.definition}</p>
              <p className="mt-2 text-xs text-text-secondary">
                {entry.pageTitle || hostnameOf(entry.sourceUrl)}
                {collectionName ? ` · ${collectionName}` : ""}
                {entry.timesSeen > 1 ? ` · seen ${entry.timesSeen} times` : ""}
              </p>
            </div>
            <div className="flex shrink-0 gap-sm">
              <button type="button" className="text-xs text-text-secondary underline" onClick={onEdit}>
                Edit
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

            {entry.timesSeen > 1 ? (
              <button
                type="button"
                onClick={onToggle}
                className="text-xs text-text-secondary underline"
                aria-expanded={expanded}
              >
                {expanded
                  ? "Hide contexts"
                  : `Seen in ${entry.timesSeen} contexts`}
              </button>
            ) : entry.contextSnippet ? (
              <p className="max-w-xl text-xs text-text-secondary">“{entry.contextSnippet}”</p>
            ) : null}

            {entry.confidence < 0.5 ? <Badge tone="warning">Low confidence</Badge> : null}
          </div>

          {expanded ? (
            <ul className="mt-md flex flex-col gap-sm border-l border-border pl-md">
              {sightings.map((sighting, index) => (
                <li key={`${sighting.seenAt}-${index}`} className="text-xs text-text-secondary">
                  <p>
                    {sighting.pageTitle || hostnameOf(sighting.sourceUrl ?? "")}
                    {sighting.seenAt ? (
                      <>
                        {" · "}
                        <RelativeTime iso={sighting.seenAt} />
                      </>
                    ) : null}
                  </p>
                  {sighting.contextSnippet ? (
                    <p className="mt-1 text-text-primary">“{sighting.contextSnippet}”</p>
                  ) : null}
                  {sighting.sourceUrl ? (
                    <a
                      href={sighting.sourceUrl}
                      className="mt-1 inline-block underline"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {hostnameOf(sighting.sourceUrl)}
                    </a>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </li>
  );
}
