"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";

const HITS = [
  { id: "SOURCE_014", when: "09:14", passage: "Deadline: March 15", align: "supports" },
  { id: "SOURCE_021", when: "09:27", passage: "Deadline: March 15", align: "supports" },
  { id: "SOURCE_033", when: "10:03", passage: "Deadline: March 20", align: "conflicts" },
];

export function AskBrowsingScene() {
  return (
    <SceneShell id="ask" heightVh={175}>
      {({ progress, map }) => {
        const type = map(progress, 0.05, 0.28, 0, 1);
        const answer = map(progress, 0.4, 0.7, 0, 1);
        const evidence = map(progress, 0.65, 0.95, 0, 1);
        const query = "What did I find about scholarship deadlines?";
        const typed = query.slice(0, Math.round(query.length * type));

        return (
          <div className="flex h-full flex-col gap-8">
            <header className="shrink-0 space-y-3">
              <ChapterLabel index="08" title="ASK YOUR BROWSING" />
              <h2 className="max-w-3xl font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                LOOM DOESN&apos;T JUST ANSWER.
                <span className="mt-2 block text-[var(--mk-dim)]">IT SHOWS YOU WHY.</span>
              </h2>
            </header>

            <div className="grid min-h-0 flex-1 gap-10 lg:grid-cols-2">
              <div className="space-y-6">
                <div className="border-y border-[var(--mk-border)] py-5">
                  <p className="font-mono text-[9px] tracking-[0.22em] text-[var(--mk-faint)]">
                    QUERY
                  </p>
                  <p className="mt-4 min-h-[4rem] font-display text-xl leading-snug tracking-tight text-[var(--mk-text)] md:text-2xl">
                    {typed}
                    <span className="ml-0.5 inline-block h-5 w-[2px] bg-[var(--mk-text)] align-middle opacity-70" />
                  </p>
                </div>

                <div
                  className="border-y border-[var(--mk-border)] py-5"
                  style={{
                    opacity: answer,
                    transform: `translate3d(0, ${(1 - answer) * 12}px, 0)`,
                  }}
                >
                  <p className="font-mono text-[9px] tracking-[0.22em] text-[var(--mk-faint)]">
                    ANSWER
                  </p>
                  <p className="mt-4 text-[15px] leading-relaxed text-[var(--mk-text)]">
                    You found three relevant sources. Two list March 15. One PDF lists March 20.
                  </p>
                </div>
              </div>

              <ul className="flex flex-col justify-center gap-5">
                {HITS.map((hit, i) => {
                  const t = map(evidence, i * 0.12, 0.4 + i * 0.12, 0, 1);
                  return (
                    <li
                      key={hit.id}
                      style={{
                        opacity: t,
                        transform: `translate3d(${(1 - t) * 10}px, 0, 0)`,
                      }}
                    >
                      <Signal
                        kind={hit.id}
                        body={hit.passage}
                        meta={`${hit.when} · ${hit.align}`}
                      />
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
