"use client";

import Image from "next/image";
import Link from "next/link";

import { ChapterLabel } from "./signal";
import { SceneShell } from "./scene-shell";
import { Thread, ThreadCanvas, threadPath } from "./thread";

export function FinalScene() {
  return (
    <SceneShell id="resolve" heightVh={165}>
      {({ progress, map }) => {
        const converge = map(progress, 0, 0.45, 0, 1);
        const product = map(progress, 0.35, 0.75, 0, 1);
        const cta = map(progress, 0.65, 1, 0, 1);

        return (
          <div className="flex h-full flex-col gap-8">
            <header className="shrink-0">
              <ChapterLabel index="11" title="RESOLUTION" />
            </header>

            <div className="relative h-24 shrink-0 opacity-50" aria-hidden>
              <ThreadCanvas viewBox="0 0 1000 120">
                <Thread d={threadPath(40, 60, 500, 60)} progress={converge} />
                <Thread d={threadPath(960, 60, 500, 60)} progress={converge} />
                <Thread d={threadPath(500, 10, 500, 60)} progress={converge} muted />
                <Thread d={threadPath(500, 110, 500, 60)} progress={converge} muted />
              </ThreadCanvas>
            </div>

            <div
              className="shrink-0 border-y border-[var(--mk-border)] py-6"
              style={{
                opacity: product,
                transform: `translate3d(0, ${(1 - product) * 14}px, 0)`,
              }}
            >
              <div className="mb-6 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <Image
                    src="/brand/loom-mark-flat.png"
                    alt=""
                    width={28}
                    height={22}
                    className="h-5 w-auto bg-transparent"
                  />
                  <span className="font-display text-sm font-semibold tracking-tight">
                    LOOM
                  </span>
                </div>
                <span className="font-mono text-[9px] tracking-[0.2em] text-[var(--mk-faint)]">
                  OVERVIEW · LIVE
                </span>
              </div>
              <div className="grid gap-6 md:grid-cols-3">
                {[
                  ["CAPTURE", "Queued signals → structured stores"],
                  ["CONNECT", "Sources linked to claims"],
                  ["ASK", "Answers with provenance"],
                ].map(([title, body]) => (
                  <div key={title}>
                    <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--mk-faint)]">
                      {title}
                    </p>
                    <p className="mt-2 text-sm text-[var(--mk-dim)]">{body}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-auto text-center" style={{ opacity: cta }}>
              <h2 className="font-display text-4xl font-semibold tracking-tight text-[var(--mk-text)] md:text-6xl">
                LOOM
              </h2>
              <p className="mt-3 font-display text-xl text-[var(--mk-dim)] md:text-2xl">
                KEEP THE THREAD.
              </p>
              <p className="mx-auto mt-3 max-w-md text-sm text-[var(--mk-dim)]">
                Turn scattered browsing into structured memory.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                <Link
                  href="/sign-up"
                  className="inline-flex items-center justify-center border border-[var(--mk-text)] bg-[var(--mk-text)] px-6 py-3 font-mono text-[11px] tracking-[0.18em] text-[var(--mk-bg)] transition-opacity hover:opacity-90"
                >
                  GET LOOM
                </Link>
                <a
                  href="#capture"
                  className="inline-flex items-center justify-center border border-[var(--mk-border-strong)] px-6 py-3 font-mono text-[11px] tracking-[0.18em] text-[var(--mk-text)] transition-colors hover:border-[var(--mk-text)]"
                >
                  SEE HOW IT WORKS
                </a>
                <Link
                  href="/overview"
                  className="inline-flex items-center justify-center px-2 py-3 font-mono text-[11px] tracking-[0.18em] text-[var(--mk-faint)] hover:text-[var(--mk-dim)]"
                >
                  OPEN DASHBOARD →
                </Link>
              </div>
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
