"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";

const MEMORY = [
  { kind: "SOURCE", body: "SOURCE_014" },
  { kind: "CLAIM", body: "Funding cutoff" },
  { kind: "EVIDENCE", body: "March 15 quote" },
  { kind: "TOPIC", body: "Admissions" },
  { kind: "DOCUMENT", body: "research-paper.pdf" },
  { kind: "DEADLINE", body: "March 15 / 20" },
  { kind: "CONFLICT", body: "2 sources disagree" },
  { kind: "ASK", body: "Scholarship deadlines?" },
];

export function MemoryScene() {
  return (
    <SceneShell id="memory" heightVh={160}>
      {({ progress, map }) => {
        const accumulate = map(progress, 0.05, 0.75, 0, 1);

        return (
          <div className="flex h-full flex-col gap-8">
            <header className="shrink-0 space-y-4">
              <ChapterLabel index="07" title="MEMORY" />
              <h2 className="max-w-2xl font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                YOUR RESEARCH
                <span className="mt-2 block text-[var(--mk-dim)]">HAS A MEMORY NOW.</span>
              </h2>
              <p className="max-w-md text-[15px] text-[var(--mk-dim)]">
                LOOM didn&apos;t just save a page. It remembered the context.
              </p>
            </header>

            <div className="grid min-h-0 flex-1 grid-cols-1 content-start gap-x-10 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
              {MEMORY.map((item, i) => {
                const t = map(accumulate, i * 0.06, 0.28 + i * 0.06, 0, 1);
                return (
                  <div
                    key={item.kind}
                    style={{
                      opacity: t,
                      transform: `translate3d(0, ${(1 - t) * 14}px, 0)`,
                    }}
                  >
                    <Signal kind={item.kind} body={item.body} />
                  </div>
                );
              })}
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
