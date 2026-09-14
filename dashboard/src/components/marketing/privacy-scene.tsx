"use client";

import { ChapterLabel, Signal } from "./signal";
import { SceneShell } from "./scene-shell";

const CONTROLS = [
  { label: "HIGHLIGHTS", state: "ON" },
  { label: "COPIES", state: "ON" },
  { label: "PAGE OPENS", state: "OFF" },
  { label: "LOCAL-ONLY DOMAINS", state: "3" },
];

export function PrivacyScene() {
  return (
    <SceneShell id="privacy" heightVh={145}>
      {({ progress, map }) => {
        const show = map(progress, 0.1, 0.55, 0, 1);

        return (
          <div className="grid h-full grid-cols-1 items-center gap-12 lg:grid-cols-2">
            <div style={{ opacity: show }} className="space-y-5">
              <ChapterLabel index="10" title="PRIVACY" />
              <h2 className="font-display text-3xl font-semibold tracking-tight text-[var(--mk-text)] md:text-5xl">
                YOUR BROWSER IS PRIVATE.
                <span className="mt-2 block text-[var(--mk-dim)]">
                  YOUR MEMORY SHOULD BE TOO.
                </span>
              </h2>
              <p className="max-w-md text-[15px] leading-relaxed text-[var(--mk-dim)]">
                Per-signal controls. Domain exclusions. Local-only mode. Visible capture
                state. Delete and export when you want out.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              {CONTROLS.map((row, i) => (
                <div
                  key={row.label}
                  style={{
                    opacity: map(progress, 0.15 + i * 0.08, 0.45 + i * 0.08, 0, 1),
                  }}
                >
                  <Signal kind={row.label} meta={`STATE · ${row.state}`} />
                </div>
              ))}
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
