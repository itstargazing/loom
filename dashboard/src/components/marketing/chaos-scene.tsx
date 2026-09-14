"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";

const FRAGMENTS = [
  { kind: "ARTICLE", body: "According to the study…" },
  { kind: "PDF", body: "research-paper.pdf", meta: "SOURCE_07" },
  { kind: "TAB", body: "university.edu" },
  { kind: "QUOTE", body: "“…the deadline is…”" },
  { kind: "CLAIM", body: "Application deadline: March 15" },
  { kind: "NOTE", body: "need to verify this" },
];

export function ChaosScene() {
  return (
    <SceneShell id="chaos" heightVh={160}>
      {({ progress, map }) => {
        const line = map(progress, 0.55, 0.9, 0, 1);

        return (
          <div className="flex h-full flex-col gap-8">
            <header className="shrink-0 space-y-4">
              <ChapterLabel index="02" title="THE CHAOS" />
              <h2 className="max-w-xl font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-4xl">
                Research is scattered
                <span className="text-[var(--mk-dim)]"> across tabs, PDFs, and notes.</span>
              </h2>
            </header>

            <div className="grid min-h-0 flex-1 grid-cols-1 gap-x-10 gap-y-6 sm:grid-cols-2 lg:grid-cols-3 content-start">
              {FRAGMENTS.map((frag, i) => {
                const local = map(progress, i * 0.07, 0.25 + i * 0.07, 0, 1);
                return (
                  <div
                    key={frag.kind}
                    style={{
                      opacity: local,
                      transform: `translate3d(0, ${(1 - local) * 16}px, 0)`,
                    }}
                  >
                    <Signal kind={frag.kind} body={frag.body} meta={frag.meta} />
                  </div>
                );
              })}
            </div>

            <div
              className="shrink-0 border-t border-[var(--mk-border)] pt-6"
              style={{ opacity: line }}
            >
              <p className="font-display text-2xl font-semibold tracking-tight text-[var(--mk-text)] md:text-3xl">
                THE INTERNET IS CONNECTED.
              </p>
              <p className="mt-1 font-display text-2xl font-semibold tracking-tight text-[var(--mk-dim)] md:text-3xl">
                YOUR WORK ISN&apos;T.
              </p>
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
