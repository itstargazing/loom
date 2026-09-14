"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";

export function ContradictionScene() {
  return (
    <SceneShell id="contradiction" heightVh={165}>
      {({ progress, map }) => {
        const approach = map(progress, 0, 0.4, 0, 1);
        const collide = map(progress, 0.35, 0.6, 0, 1);
        const reveal = map(progress, 0.55, 0.9, 0, 1);

        return (
          <div className="flex h-full flex-col gap-8">
            <header className="shrink-0 space-y-3">
              <ChapterLabel index="06" title="CONTRADICTION" />
              <h2 className="max-w-2xl font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                LOOM DOESN&apos;T HIDE
                <span className="mt-2 block text-[var(--mk-dim)]">THE CONFLICT.</span>
              </h2>
            </header>

            <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 lg:grid-cols-3 lg:items-center">
              <div
                style={{
                  opacity: 0.35 + approach * 0.65,
                  transform: `translate3d(${approach * 8}px, 0, 0)`,
                }}
              >
                <Signal
                  kind="SOURCE_014"
                  body="Deadline: March 15"
                  meta="UNIVERSITY WEBSITE"
                />
              </div>

              <div
                className="text-center"
                style={{ opacity: collide }}
              >
                <p className="font-mono text-[9px] tracking-[0.28em] text-[var(--mk-text)]">
                  CONFLICT DETECTED
                </p>
                <p className="mt-5 font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-4xl">
                  MARCH 15
                  <span className="mx-3 text-[var(--mk-faint)]">≠</span>
                  MARCH 20
                </p>
              </div>

              <div
                style={{
                  opacity: 0.35 + approach * 0.65,
                  transform: `translate3d(${-approach * 8}px, 0, 0)`,
                }}
              >
                <Signal kind="SOURCE_021" body="Deadline: March 20" meta="PDF" />
              </div>
            </div>

            <div
              className="shrink-0 flex flex-col gap-2 border-t border-[var(--mk-border)] pt-6 sm:flex-row sm:items-end sm:justify-between"
              style={{ opacity: reveal }}
            >
              <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--mk-dim)]">
                2 SOURCES · 1 CONFLICT · 0 GUESSING
              </p>
              <p className="max-w-sm text-sm text-[var(--mk-dim)]">
                It shows you where the disagreement came from.
              </p>
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
