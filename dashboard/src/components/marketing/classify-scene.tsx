"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";

export function ClassifyScene() {
  return (
    <SceneShell id="classify" heightVh={165}>
      {({ progress, map }) => {
        const enter = map(progress, 0, 0.2, 0, 1);
        const split = map(progress, 0.2, 0.75, 0, 1);

        const parts = [
          { kind: "QUOTE", body: "…after March 15…" },
          { kind: "CLAIM", body: "Funding cutoff" },
          { kind: "DEADLINE", body: "March 15" },
          { kind: "SOURCE", body: "SOURCE_07" },
        ];

        return (
          <div className="flex h-full flex-col gap-8">
            <header className="shrink-0 space-y-4" style={{ opacity: enter }}>
              <ChapterLabel index="04" title="CLASSIFY" />
              <h2 className="max-w-2xl font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                SCATTERED INFORMATION
                <span className="mt-2 block text-[var(--mk-dim)]">
                  BECOMES STRUCTURED MEMORY.
                </span>
              </h2>
            </header>

            <div className="grid min-h-0 flex-1 grid-cols-1 items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
              <div
                style={{
                  opacity: 1 - split * 0.25,
                  transform: `scale(${1 - split * 0.03})`,
                }}
              >
                <Signal
                  kind="RAW SIGNAL"
                  body="Applications submitted after March 15 will not be considered…"
                  meta="IN → LOOM"
                />
              </div>

              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                {parts.map((part, i) => {
                  const t = map(split, i * 0.12, 0.4 + i * 0.12, 0, 1);
                  return (
                    <div
                      key={part.kind}
                      className="rounded-sm border border-[var(--mk-border)] px-4 py-3"
                      style={{
                        opacity: t,
                        transform: `translate3d(0, ${(1 - t) * 18}px, 0)`,
                      }}
                    >
                      <Signal kind={part.kind} body={part.body} />
                    </div>
                  );
                })}
              </div>
            </div>

            <p
              className="shrink-0 font-mono text-[9px] tracking-[0.28em] text-[var(--mk-faint)]"
              style={{ opacity: map(progress, 0.7, 1, 0, 1) }}
            >
              CAPTURE → CLASSIFY → ROUTE
            </p>
          </div>
        );
      }}
    </SceneShell>
  );
}
