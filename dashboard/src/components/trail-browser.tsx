"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";

import { RelativeTime } from "@/components/relative-time";
import { SourceLink } from "@/components/source-link";
import { hostnameOf } from "@/lib/format";
import type { Trail, TrailNode } from "@/lib/types";

export function TrailBrowser({ trail }: { trail: Trail }) {
  const router = useRouter();
  const byId = useMemo(() => new Map(trail.nodes.map((node) => [node.id, node])), [trail.nodes]);

  if (trail.nodes.length === 0) {
    return (
      <div className="loom-glass loom-sheen-mid w-full px-xl py-xl text-sm text-text-secondary">
        No captures yet, so there is no trail to replay.
      </div>
    );
  }

  function askAbout(node: TrailNode) {
    const q = node.snippet
      ? `What do I know about: ${node.snippet.slice(0, 120)}`
      : `What did I capture from ${node.pageTitle || node.sourceUrl}?`;
    router.push(`/ask?q=${encodeURIComponent(q)}`);
  }

  return (
    <ol className="flex w-full flex-col gap-md">
      {trail.nodes.map((node, index) => {
        const inbound = trail.edges.filter((edge) => edge.target === node.id);
        const from = inbound[0] ? byId.get(inbound[0].source) : null;
        return (
          <li key={node.id} className="loom-glass loom-sheen-mid flex w-full flex-col gap-sm px-xl py-xl">
            <div className="flex flex-wrap items-center justify-between gap-md">
              <span className="loom-badge">
                {String(index + 1).padStart(2, "0")}
                {inbound[0] ? ` · ${inbound[0].kind.replace("_", " ")}` : ""}
              </span>
              <span className="font-mono text-xs text-text-secondary">
                {node.categories.join(" · ") || "unclassified"}
              </span>
            </div>
            <p className="text-sm text-text-primary">
              {node.snippet || node.pageTitle || node.sourceUrl}
            </p>
            {from ? (
              <p className="text-xs text-text-faint">
                from {from.pageTitle || hostnameOf(from.sourceUrl)}
              </p>
            ) : null}
            <SourceLink href={node.sourceUrl}>
              {node.pageTitle || hostnameOf(node.sourceUrl)}
            </SourceLink>
            <p className="text-xs text-text-faint">
              <RelativeTime iso={node.occurredAt} />
            </p>
            <div>
              <button
                type="button"
                className="loom-btn loom-btn-secondary"
                onClick={() => askAbout(node)}
              >
                Ask about this
              </button>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
