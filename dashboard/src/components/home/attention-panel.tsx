import Link from "next/link";

import type { AttentionItem } from "@/lib/home-view";

function DashList({
  items,
  empty,
}: {
  items: AttentionItem[];
  empty: string;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-text-secondary">{empty}</p>;
  }

  return (
    <ul>
      {items.map((item, index) => (
        <li
          key={`${item.href}-${item.label}`}
          className={
            index === 0
              ? "py-sm"
              : "border-t border-border-soft py-sm"
          }
        >
          <Link
            href={item.href}
            className="text-sm text-text-primary transition-colors duration-fast hover:text-text-secondary"
          >
            <span className="mr-sm text-text-faint">—</span>
            {item.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function AttentionPanel({
  unresolved,
  routeNext,
  facts,
}: {
  unresolved: AttentionItem[];
  routeNext: AttentionItem[];
  facts: string;
}) {
  return (
    <section className="loom-glass loom-sheen-bl px-lg py-lg sm:px-xl sm:py-xl">
      <div className="mb-lg flex items-center justify-between gap-md">
        <span className="loom-badge">↘ What needs attention</span>
        <span className="font-mono text-[10px] tracking-[0.28em] text-text-faint">
          LOOM
        </span>
      </div>

      <div className="grid grid-cols-1 gap-lg min-[640px]:grid-cols-3">
        <div>
          <h2 className="loom-display font-display mb-sm text-lg font-medium">Unresolved</h2>
          <DashList
            items={unresolved}
            empty="No open conflicts or failed classifications. New flags will land here."
          />
        </div>

        <div className="loom-glass loom-glass-bright loom-glass-nested loom-sheen-tr px-md py-md">
          <h2 className="loom-display font-display mb-sm text-lg font-medium">Route next</h2>
          <DashList
            items={routeNext}
            empty="Once a highlight matches, it will land in a skill store."
          />
        </div>

        <div>
          <h2 className="loom-display font-display mb-sm text-lg font-medium">Facts</h2>
          <p className="text-sm text-text-secondary">{facts}</p>
        </div>
      </div>
    </section>
  );
}
