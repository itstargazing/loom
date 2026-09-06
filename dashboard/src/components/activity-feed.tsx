import Link from "next/link";

import { formatConfidence, hostnameOf } from "@/lib/format";
import type { ActivityItem } from "@/lib/types";

import { RelativeTime } from "./relative-time";

/**
 * Newest entries across every skill store, interleaved.
 *
 * The backend flattens the eight stores into a shared shape, so this list shows
 * a title and a detail line regardless of which store an entry came from.
 */
export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <ul className="flex flex-col divide-y divide-border rounded-glass border border-border">
      {items.map((item, index) => (
        <li
          key={`${item.skill}-${index}`}
          className="flex flex-col gap-xs p-md transition-colors duration-fast hover:bg-glass"
        >
          <div className="flex items-center justify-between gap-md">
            <span className="loom-badge">
              {item.label}
            </span>
            <span className="text-xs text-text-secondary">
              <RelativeTime iso={item.lastSeenAt} />
            </span>
          </div>

          <p className="text-sm">{item.title}</p>
          {item.detail ? (
            <p className="text-sm text-text-secondary">{item.detail}</p>
          ) : null}

          <div className="flex items-center gap-md text-xs text-text-secondary">
            <Link
              href={item.sourceUrl}
              target="_blank"
              rel="noreferrer"
              title={item.pageTitle || item.sourceUrl}
              className="underline decoration-border underline-offset-2 transition-colors duration-fast hover:text-text-primary"
            >
              {hostnameOf(item.sourceUrl)}
            </Link>
            <span className="loom-mono">{formatConfidence(item.confidence)}</span>
            {item.timesSeen > 1 ? (
              <span className="loom-mono">seen {item.timesSeen}x</span>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
