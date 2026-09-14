"use client";

import { useRef, type ReactNode } from "react";

import {
  mapRange,
  usePrefersReducedMotion,
  useSectionProgress,
} from "@/hooks/use-section-progress";

type SceneShellProps = {
  id: string;
  heightVh?: number;
  children: (ctx: {
    progress: number;
    reduced: boolean;
    map: typeof mapRange;
  }) => ReactNode;
  className?: string;
};

/**
 * One chapter owns the viewport while pinned.
 * Solid stage background prevents previous scenes from bleeding through.
 */
export function SceneShell({
  id,
  heightVh = 170,
  children,
  className = "",
}: SceneShellProps) {
  const ref = useRef<HTMLElement>(null);
  const progress = useSectionProgress(ref);
  const reduced = usePrefersReducedMotion();

  return (
    <section
      id={id}
      ref={ref}
      className={`mk-scene relative ${className}`}
      style={{ height: `${heightVh}vh` }}
    >
      <div className="mk-stage sticky top-0 flex h-[100svh] w-full items-stretch overflow-hidden bg-[var(--mk-bg)]">
        <div className="mx-auto flex h-full w-full max-w-[1100px] flex-col px-6 pb-10 pt-24 md:px-12 md:pb-14 md:pt-28">
          {children({
            progress: reduced ? 1 : progress,
            reduced,
            map: mapRange,
          })}
        </div>
      </div>
    </section>
  );
}
