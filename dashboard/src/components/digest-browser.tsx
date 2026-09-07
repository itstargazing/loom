"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { RelativeTime } from "@/components/relative-time";
import { SourceLink } from "@/components/source-link";
import { Badge } from "@/components/skill-table";
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

async function act(id: string, action: string, category?: string): Promise<Digest> {
  const response = await fetch(`/api/proxy/digest/${id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, category }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  }
  return body as Digest;
}

export function DigestBrowser({ initial }: { initial: Digest }) {
  const router = useRouter();
  const [digest, setDigest] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const pendingCount = useMemo(
    () => digest.items.filter((item) => item.reviewStatus === "pending_review").length,
    [digest],
  );

  async function run(card: DigestCard, action: string, category?: string) {
    setError(null);
    try {
      setDigest(await act(card.id, action, category));
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not update");
    }
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
            {group.items.map((card) => (
              <li key={card.id} className="loom-glass loom-sheen-mid flex w-full flex-col gap-sm px-xl py-xl">
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
                  <button type="button" className="loom-btn" onClick={() => void run(card, "accept")}>
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
                      defaultValue=""
                      onChange={(event) => {
                        const value = event.target.value;
                        if (value) void run(card, "reassign", value);
                      }}
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
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
