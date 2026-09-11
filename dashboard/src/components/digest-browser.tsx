"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { RelativeTime } from "@/components/relative-time";
import { SourceLink } from "@/components/source-link";
import { Badge } from "@/components/skill-table";
import { apiErrorCode, apiErrorMessage } from "@/lib/api-error";
import { hostnameOf } from "@/lib/format";
import type { Digest, DigestCard } from "@/lib/types";

const REASSIGN: Array<{ value: string; label: string }> = [
  { value: "glossary_term", label: "Glossary" },
  { value: "citation", label: "Citations" },
  { value: "deadline", label: "Deadlines" },
  { value: "contradiction_candidate", label: "Contradiction candidates" },
  { value: "reading_highlight", label: "Reading compiler" },
  { value: "product_listing", label: "Products" },
  { value: "job_listing", label: "Jobs" },
  { value: "contract_clause", label: "Contract flags" },
  { value: "none", label: "Unrouted" },
];

/** Categories that need extra fields before a reassign can succeed. */
const REQUIRED_FIELDS: Record<string, Array<{ key: string; label: string; type?: string }>> = {
  glossary_term: [
    { key: "term", label: "Term" },
    { key: "definition", label: "Definition" },
  ],
  citation: [{ key: "quote", label: "Quote" }],
  deadline: [
    { key: "deadline_title", label: "Title" },
    { key: "deadline_date", label: "Date", type: "date" },
  ],
  contradiction_candidate: [
    { key: "claim", label: "Claim" },
    { key: "topic", label: "Topic" },
  ],
  reading_highlight: [{ key: "passage", label: "Passage" }],
  product_listing: [{ key: "product_name", label: "Product name" }],
  job_listing: [{ key: "job_title", label: "Job title" }],
  contract_clause: [
    { key: "clause_text", label: "Clause" },
    { key: "flag_reason", label: "Why it matters" },
    { key: "risk_level", label: "Risk (low / medium / high)" },
  ],
};

function seedFields(card: DigestCard, category: string): Record<string, string> {
  const existing = card.fields ?? {};
  const seeded: Record<string, string> = {};
  for (const field of REQUIRED_FIELDS[category] ?? []) {
    const value = existing[field.key];
    if (field.key === "deadline_date") {
      seeded[field.key] =
        typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value) ? value.slice(0, 10) : "";
      continue;
    }
    if (typeof value === "string" && value.trim()) {
      seeded[field.key] = value;
      continue;
    }
    if (
      field.key === "deadline_title" ||
      field.key === "passage" ||
      field.key === "quote" ||
      field.key === "claim"
    ) {
      seeded[field.key] = card.snippet || card.pageTitle || "";
    } else if (field.key === "term") {
      seeded[field.key] = card.snippet || "";
    } else if (field.key === "product_name" || field.key === "job_title") {
      seeded[field.key] = card.pageTitle || card.snippet || "";
    } else {
      seeded[field.key] = "";
    }
  }
  return seeded;
}

async function act(
  id: string,
  action: string,
  category?: string,
  fields?: Record<string, string>,
): Promise<Digest> {
  const response = await fetch(`/api/proxy/digest/${id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, category, fields }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      apiErrorMessage(body, "Could not update this item. Check the fields and try again."),
    ) as Error & { code?: string | null; body?: unknown };
    error.code = apiErrorCode(body);
    error.body = body;
    throw error;
  }
  return body as Digest;
}

export function DigestBrowser({ initial }: { initial: Digest }) {
  const router = useRouter();
  const [digest, setDigest] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [draftCategory, setDraftCategory] = useState<Record<string, string>>({});
  const [draftFields, setDraftFields] = useState<Record<string, Record<string, string>>>({});
  const pendingCount = useMemo(
    () => digest.items.filter((item) => item.reviewStatus === "pending_review").length,
    [digest],
  );

  async function run(
    card: DigestCard,
    action: string,
    category?: string,
    fields?: Record<string, string>,
  ) {
    setError(null);
    try {
      setDigest(await act(card.id, action, category, fields));
      setDraftCategory((current) => {
        const next = { ...current };
        delete next[card.id];
        return next;
      });
      setDraftFields((current) => {
        const next = { ...current };
        delete next[card.id];
        return next;
      });
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not update");
    }
  }

  function chooseCategory(card: DigestCard, category: string) {
    if (!category) return;
    if (REQUIRED_FIELDS[category]) {
      setDraftCategory((current) => ({ ...current, [card.id]: category }));
      setDraftFields((current) => ({
        ...current,
        [card.id]: seedFields(card, category),
      }));
      setError(null);
      return;
    }
    void run(card, "reassign", category);
  }

  function submitReassign(event: FormEvent, card: DigestCard) {
    event.preventDefault();
    const category = draftCategory[card.id];
    if (!category) return;
    void run(card, "reassign", category, draftFields[card.id]);
  }

  if (digest.items.length === 0) {
    return (
      <div className="loom-glass loom-sheen-mid w-full px-xl py-xl text-sm text-text-secondary">
        Nothing captured in the last 24 hours. Browse, highlight, or copy, then come back.
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-lg">
      <p className="text-sm text-text-secondary">
        {digest.items.length} items · {pendingCount} need a look before they land in a store
      </p>
      {error ? <p className="text-sm text-error">{error}</p> : null}
      {digest.groups.map((group) => (
        <section key={group.key} className="flex w-full flex-col gap-md">
          <h2 className="font-mono text-xs tracking-wide text-text-secondary">{group.label}</h2>
          <ul className="flex w-full flex-col gap-md">
            {group.items.map((card) => {
              const pendingCategory = draftCategory[card.id];
              const pendingSpecs = pendingCategory ? REQUIRED_FIELDS[pendingCategory] : null;
              return (
                <li
                  key={card.id}
                  className="loom-glass loom-sheen-mid flex w-full flex-col gap-sm px-xl py-xl"
                >
                  <div className="flex flex-wrap items-center justify-between gap-md">
                    <span className="loom-badge">
                      {card.groupLabel || card.categories.join(" · ") || "none"}
                    </span>
                    <span className="font-mono text-xs text-text-secondary">
                      {Math.round(card.confidence * 100)}% · {card.provider}
                    </span>
                  </div>
                  {card.reviewStatus === "pending_review" ? (
                    <Badge tone="warning">Needs review</Badge>
                  ) : null}
                  <p className="text-sm text-text-primary">{card.snippet || "(no snippet)"}</p>
                  {card.reason ? (
                    <p className="text-xs text-text-secondary">{card.reason}</p>
                  ) : null}
                  <SourceLink href={card.sourceUrl}>
                    {card.pageTitle || hostnameOf(card.sourceUrl)}
                  </SourceLink>
                  <p className="text-xs text-text-faint">
                    <RelativeTime iso={card.occurredAt} />
                  </p>
                  <div className="flex flex-wrap items-end gap-sm">
                    <button
                      type="button"
                      className="loom-btn"
                      onClick={() => void run(card, "accept")}
                    >
                      Accept
                    </button>
                    <button
                      type="button"
                      className="loom-btn loom-btn-secondary"
                      onClick={() => void run(card, "discard")}
                    >
                      Discard
                    </button>
                    <label className="flex min-w-[10rem] flex-col gap-1">
                      <span className="font-mono text-xs text-text-secondary">Reassign</span>
                      <select
                        className="loom-input"
                        value={pendingCategory ?? ""}
                        onChange={(event) => chooseCategory(card, event.target.value)}
                      >
                        <option value="">Choose…</option>
                        {REASSIGN.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  {pendingSpecs ? (
                    <form
                      onSubmit={(event) => submitReassign(event, card)}
                      className="mt-sm flex w-full flex-col gap-sm border-t border-border-soft pt-sm"
                    >
                      <p className="text-xs text-text-secondary">
                        Fill these in to file under{" "}
                        {REASSIGN.find((item) => item.value === pendingCategory)?.label ??
                          pendingCategory}
                        .
                      </p>
                      {pendingSpecs.map((field) => (
                        <label key={field.key} className="flex w-full flex-col gap-1">
                          <span className="font-mono text-xs text-text-secondary">
                            {field.label}
                          </span>
                          {field.type === "date" ? (
                            <input
                              type="date"
                              className="loom-input"
                              required
                              value={draftFields[card.id]?.[field.key] ?? ""}
                              onChange={(event) =>
                                setDraftFields((current) => ({
                                  ...current,
                                  [card.id]: {
                                    ...(current[card.id] ?? {}),
                                    [field.key]: event.target.value,
                                  },
                                }))
                              }
                            />
                          ) : (
                            <input
                              type="text"
                              className="loom-input"
                              required
                              value={draftFields[card.id]?.[field.key] ?? ""}
                              onChange={(event) =>
                                setDraftFields((current) => ({
                                  ...current,
                                  [card.id]: {
                                    ...(current[card.id] ?? {}),
                                    [field.key]: event.target.value,
                                  },
                                }))
                              }
                            />
                          )}
                        </label>
                      ))}
                      <div className="flex flex-wrap gap-sm">
                        <button type="submit" className="loom-btn">
                          File as{" "}
                          {REASSIGN.find((item) => item.value === pendingCategory)?.label ??
                            "category"}
                        </button>
                        <button
                          type="button"
                          className="loom-btn loom-btn-secondary"
                          onClick={() => {
                            setDraftCategory((current) => {
                              const next = { ...current };
                              delete next[card.id];
                              return next;
                            });
                            setDraftFields((current) => {
                              const next = { ...current };
                              delete next[card.id];
                              return next;
                            });
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
