import Link from "next/link";

import { SyncCta } from "./sync-cta";
import { ThreadIllustration } from "./thread-illustration";

export function HeroPanel({
  headline,
  empty,
}: {
  headline: [string, string];
  empty: boolean;
}) {
  return (
    <section className="loom-glass loom-glass-bright loom-sheen-tl px-xl py-xl">
      <div className="grid items-center gap-xl md:grid-cols-[1.2fr_0.8fr]">
        <div className="flex flex-col gap-lg">
          <span className="loom-badge w-fit">
            <span
              aria-hidden="true"
              className="h-1.5 w-1.5 rounded-pill bg-[var(--text)]"
            />
            Welcome back
          </span>
          <h1 className="loom-display font-display text-[2rem] font-semibold leading-[1.15] tracking-tight sm:text-[2.35rem]">
            {headline[0]}
            <span className="mt-1 block font-medium text-text-faint">
              {headline[1]}
            </span>
          </h1>
          <div className="flex items-center gap-sm">
            <SyncCta />
            <Link
              href="/privacy"
              className="loom-icon-btn"
              aria-label="Local-only mode"
              title="Local-only mode"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M4.2 7.2V5.6a3.8 3.8 0 0 1 7.6 0v1.6"
                  stroke="currentColor"
                  strokeWidth="1.25"
                />
                <rect
                  x="3"
                  y="7.2"
                  width="10"
                  height="6.4"
                  rx="1.6"
                  stroke="currentColor"
                  strokeWidth="1.25"
                />
              </svg>
            </Link>
          </div>
          {empty ? (
            <p className="max-w-sm text-sm text-text-secondary">
              Load the unpacked extension from{" "}
              <span className="loom-mono">extension/dist</span>, leave Highlights
              on, and select a short term. Sync files it here.
            </p>
          ) : null}
        </div>
        <ThreadIllustration className="mx-auto w-full max-w-[280px]" />
      </div>
    </section>
  );
}
