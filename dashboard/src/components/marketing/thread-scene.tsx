"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";
import { Thread, ThreadCanvas, ThreadNode, threadPath } from "./thread";

const NODES = [
  { id: "S1", label: "SOURCE_001", sub: "University page", x: 160, y: 140 },
  { id: "S2", label: "SOURCE_002", sub: "PDF", x: 840, y: 120 },
  { id: "C1", label: "CLAIM", sub: "A deadline exists", x: 500, y: 260 },
  { id: "E1", label: "EVIDENCE", sub: "Quote · March 15", x: 500, y: 420 },
];

export function ThreadScene() {
  return (
    <SceneShell id="connect" heightVh={170}>
      {({ progress, map }) => {
        const draw = map(progress, 0.05, 0.7, 0, 1);
        const list = map(progress, 0.2, 0.85, 0, 1);

        const edges = [
          threadPath(160, 140, 500, 260),
          threadPath(840, 120, 500, 260),
          threadPath(500, 260, 500, 420),
        ];

        return (
          <div className="flex h-full flex-col gap-6">
            <header className="shrink-0 space-y-3">
              <ChapterLabel index="05" title="CONNECT" />
              <h2 className="font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                THREADS ARE
                <span className="text-[var(--mk-dim)]"> RELATIONSHIPS.</span>
              </h2>
            </header>

            <div className="grid min-h-0 flex-1 gap-8 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="relative min-h-[240px] border border-[var(--mk-border)] bg-[rgba(255,255,255,0.015)]">
                <ThreadCanvas viewBox="0 0 1000 520" className="absolute inset-0 p-2">
                  {edges.map((d, i) => (
                    <Thread
                      key={d}
                      d={d}
                      progress={map(draw, i * 0.1, 0.4 + i * 0.12, 0, 1)}
                      active={draw > 0.5}
                    />
                  ))}
                  {NODES.map((node) => (
                    <g key={node.id}>
                      <ThreadNode x={node.x} y={node.y} active={draw > 0.25} r={3.5} />
                      <text
                        x={node.x + 10}
                        y={node.y + 4}
                        fill="currentColor"
                        opacity={0.55}
                        style={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }}
                      >
                        {node.label}
                      </text>
                    </g>
                  ))}
                </ThreadCanvas>
              </div>

              <ul className="flex flex-col justify-center gap-4">
                {NODES.map((node, i) => {
                  const t = map(list, i * 0.1, 0.35 + i * 0.1, 0, 1);
                  return (
                    <li
                      key={node.id}
                      style={{
                        opacity: t,
                        transform: `translate3d(${(1 - t) * 12}px, 0, 0)`,
                      }}
                    >
                      <Signal kind={node.label} body={node.sub} />
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
