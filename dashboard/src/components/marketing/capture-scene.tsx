"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";

const ARTICLE = `Graduate admissions for Fall 2026 open on January 2.
Applications submitted after March 15 will not be considered for funding.
Candidates should upload transcripts as a single PDF.`;

export function CaptureScene() {
  return (
    <SceneShell id="capture" heightVh={170}>
      {({ progress, map }) => {
        const highlight = map(progress, 0.05, 0.3, 0, 1);
        const lift = map(progress, 0.3, 0.6, 0, 1);
        const captured = map(progress, 0.55, 0.9, 0, 1);

        return (
          <div className="flex h-full flex-col gap-8">
            <header className="shrink-0 space-y-3">
              <ChapterLabel index="03" title="CAPTURE" />
              <h2 className="font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                TEXT LEAVES
                <span className="text-[var(--mk-dim)]"> THE PAGE.</span>
              </h2>
            </header>

            <div className="grid min-h-0 flex-1 gap-10 lg:grid-cols-2 lg:items-start">
              <article className="border-y border-[var(--mk-border)] py-6">
                <p className="font-mono text-[9px] tracking-[0.22em] text-[var(--mk-faint)]">
                  university.edu / admissions
                </p>
                <p className="mt-5 whitespace-pre-line text-[15px] leading-8 text-[var(--mk-dim)]">
                  {ARTICLE.split("\n").map((line, idx) => {
                    const isTarget = line.includes("March 15");
                    if (!isTarget) {
                      return (
                        <span key={idx}>
                          {line}
                          {"\n"}
                        </span>
                      );
                    }
                    return (
                      <span key={idx}>
                        <span
                          style={{
                            backgroundColor: `rgba(244, 241, 234, ${0.1 * highlight})`,
                            opacity: 1 - lift * 0.4,
                          }}
                        >
                          {line}
                        </span>
                        {"\n"}
                      </span>
                    );
                  })}
                </p>
              </article>

              <div className="flex flex-col justify-center gap-8">
                <div
                  style={{
                    opacity: Math.max(lift * 0.85, captured > 0 ? 0 : 0),
                    transform: `translate3d(0, ${-lift * 12}px, 0)`,
                  }}
                >
                  <Signal
                    kind="HIGHLIGHT"
                    body="Applications submitted after March 15 will not be considered…"
                  />
                </div>
                <div
                  className="border border-[var(--mk-border)] px-4 py-4"
                  style={{
                    opacity: captured,
                    transform: `translate3d(0, ${(1 - captured) * 16}px, 0)`,
                  }}
                >
                  <Signal
                    kind="CAPTURED"
                    body="Applications submitted after March 15 will not be considered…"
                    meta="SOURCE_07 · 12:42:18"
                  />
                </div>
              </div>
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
