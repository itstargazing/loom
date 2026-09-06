import Link from "next/link";
import type { ReactNode } from "react";

import { formatCount } from "@/lib/format";

import { ThreadSpark } from "./thread-illustration";

function OrbIcon({ children }: { children: ReactNode }) {
  return (
    <span className="flex h-10 w-10 items-center justify-center rounded-pill border border-border-soft bg-glass-2">
      {children}
    </span>
  );
}

export function StatsRow({
  signalsWoven,
  signalsLastDay,
  classified,
  localOnlyDomains,
  localOnlyActive,
}: {
  signalsWoven: number;
  signalsLastDay: number;
  classified: number;
  localOnlyDomains: number;
  localOnlyActive: boolean;
}) {
  return (
    <section className="grid grid-cols-1 gap-md max-[640px]:grid-cols-1 min-[640px]:grid-cols-[1.3fr_1fr]">
      <div className="loom-glass loom-sheen-mid px-lg py-lg">
        <span className="loom-badge">All time</span>
        <ThreadSpark className="mt-lg w-full" />
        <h2 className="loom-display font-display mt-lg text-2xl font-semibold tracking-tight">
          {formatCount(signalsWoven)} signals woven
        </h2>
        <p className="mt-xs text-sm text-text-secondary">
          {signalsWoven === 0
            ? "The first highlight, copy, or dwell will appear here after sync."
            : `${formatCount(signalsLastDay)} captured in the last 24 hours.`}
        </p>
      </div>

      <div className="flex flex-col gap-md">
        <div className="loom-glass loom-sheen-tr flex items-center gap-md px-lg py-lg">
          <OrbIcon>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path
                d="M3 11 C6 4 10 4 13 11"
                stroke="currentColor"
                strokeWidth="1.25"
                strokeLinecap="round"
              />
              <circle cx="8" cy="6" r="1.4" fill="currentColor" />
            </svg>
          </OrbIcon>
          <div>
            <p className="font-mono text-2xl font-semibold leading-none">
              {formatCount(classified)}
            </p>
            <p className="mt-xs font-mono text-xs text-text-secondary">
              Classified
            </p>
          </div>
        </div>

        <Link
          href="/privacy"
          className="loom-glass loom-glass-interactive loom-sheen-bl flex items-center gap-md px-lg py-lg"
        >
          <OrbIcon>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="5.2" stroke="currentColor" strokeWidth="1.25" />
              <path d="M8 4.4 V8 L10.4 10" stroke="currentColor" strokeWidth="1.25" />
            </svg>
          </OrbIcon>
          <div>
            <p className="font-mono text-2xl font-semibold leading-none">
              {localOnlyActive ? formatCount(localOnlyDomains) : "Off"}
            </p>
            <p className="mt-xs font-mono text-xs text-text-secondary">
              {localOnlyActive
                ? "Local-only domains"
                : "Local-only mode"}
            </p>
          </div>
        </Link>
      </div>
    </section>
  );
}
