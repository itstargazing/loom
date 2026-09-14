"use client";

import Image from "next/image";

import { ChapterLabel } from "./signal";
import { SceneShell } from "./scene-shell";
import { Thread, ThreadCanvas } from "./thread";

export function HeroVoid() {
  return (
    <SceneShell id="void" heightVh={140}>
      {({ progress, map }) => {
        const fadeIn = map(progress, 0, 0.25, 0, 1);
        const threads = map(progress, 0.1, 0.7, 0, 1);

        return (
          <div className="flex h-full flex-col justify-between gap-10">
            <div className="relative min-h-0 flex-1">
              <div
                className="pointer-events-none absolute inset-0 opacity-30"
                aria-hidden
              >
                <ThreadCanvas viewBox="0 0 1000 560">
                  <Thread d="M 60 400 C 240 260, 360 480, 560 240" progress={threads} />
                  <Thread
                    d="M 140 160 C 300 100, 480 240, 760 140"
                    progress={threads * 0.8}
                    muted
                  />
                </ThreadCanvas>
              </div>

              <div className="relative z-10 max-w-3xl pt-4" style={{ opacity: fadeIn }}>
                <div className="mb-10 flex items-center gap-4">
                  <Image
                    src="/brand/loom-mark-flat.png"
                    alt=""
                    width={36}
                    height={28}
                    className="h-7 w-auto bg-transparent"
                    priority
                  />
                  <ChapterLabel index="01" title="THE VOID" />
                </div>

                <p className="font-mono text-[9px] tracking-[0.32em] text-[var(--mk-faint)]">
                  BROWSER MEMORY / 01
                </p>
                <h1 className="mt-6 font-display text-[clamp(2.75rem,7.5vw,5.75rem)] font-semibold leading-[0.94] text-[var(--mk-text)]">
                  THE MEMORY LAYER
                  <span className="mt-3 block font-medium text-[var(--mk-dim)]">
                    FOR YOUR BROWSER.
                  </span>
                </h1>
                <p
                  className="mt-8 max-w-md text-[15px] leading-relaxed text-[var(--mk-dim)]"
                  style={{ opacity: map(progress, 0.15, 0.45, 0, 1) }}
                >
                  Your browser remembers where you went.
                  <br />
                  LOOM remembers what mattered.
                </p>
              </div>
            </div>

            <div
              className="relative z-10 flex flex-wrap gap-x-8 gap-y-3 border-t border-[var(--mk-border)] pt-6"
              style={{ opacity: map(progress, 0.35, 0.7, 0, 1) }}
            >
              {["SOURCE", "QUOTE", "PDF", "CLAIM", "DEADLINE", "EVIDENCE"].map((label) => (
                <span
                  key={label}
                  className="font-mono text-[9px] tracking-[0.24em] text-[var(--mk-faint)]"
                >
                  {label}
                </span>
              ))}
              <span className="ml-auto font-mono text-[9px] tracking-[0.24em] text-[var(--mk-faint)]">
                CAPTURE ENGINE ONLINE
              </span>
            </div>
          </div>
        );
      }}
    </SceneShell>
  );
}
