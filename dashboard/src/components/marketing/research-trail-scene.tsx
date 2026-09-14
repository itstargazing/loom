"use client";

import { ChapterLabel } from "./signal";
import { SceneShell } from "./scene-shell";

const EVENTS = [
  { t: "09:14", label: "University page" },
  { t: "09:27", label: "PDF" },
  { t: "09:41", label: "Article" },
  { t: "10:03", label: "Scholarship page" },
  { t: "10:17", label: "PDF" },
  { t: "10:22", label: "Conflict detected" },
  { t: "10:31", label: "Question asked" },
];

export function ResearchTrailScene() {
  return (
    <SceneShell id="trail" heightVh={150}>
      {({ progress, map }) => {
        const draw = map(progress, 0.08, 0.9, 0, 1);

        return (
          <div className="flex h-full flex-col gap-10">
            <header className="shrink-0 space-y-3">
              <ChapterLabel index="09" title="RESEARCH TRAIL" />
              <h2 className="font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                SEE HOW YOU GOT THERE.
              </h2>
              <p className="font-mono text-[9px] tracking-[0.22em] text-[var(--mk-faint)]">
                Every source. Every thread. Every decision.
              </p>
            </header>

            <ol className="grid min-h-0 flex-1 content-center gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {EVENTS.map((event, i) => {
                const t = map(draw, i / EVENTS.length, (i + 0.85) / EVENTS.length, 0, 1);
                return (
                  <li
                    key={event.t}
                    className="border-t border-[var(--mk-border)] pt-4"
                    style={{
                      opacity: t,
                      transform: `translate3d(0, ${(1 - t) * 12}px, 0)`,
                    }}
                  >
                    <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--mk-faint)]">
                      {event.t}
                    </p>
                    <p className="mt-3 text-[15px] text-[var(--mk-text)]">{event.label}</p>
                  </li>
                );
              })}
            </ol>
          </div>
        );
      }}
    </SceneShell>
  );
}
