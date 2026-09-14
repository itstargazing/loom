"use client";

import { useId, useMemo, type ReactNode } from "react";

type ThreadProps = {
  d: string;
  progress?: number;
  active?: boolean;
  muted?: boolean;
  className?: string;
};

/** SVG path that draws itself with scroll progress (pathLength=1). */
export function Thread({
  d,
  progress = 1,
  active = false,
  muted = false,
  className = "",
}: ThreadProps) {
  const drawn = Math.max(0, Math.min(1, progress));
  return (
    <path
      d={d}
      pathLength={1}
      fill="none"
      stroke="currentColor"
      strokeWidth={active ? 1.25 : 0.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{
        strokeDasharray: 1,
        strokeDashoffset: 1 - drawn,
        opacity: muted ? 0.18 : active ? 0.85 : 0.45,
        transition: "opacity 200ms ease-out",
      }}
    />
  );
}

type ThreadNodeProps = {
  x: number;
  y: number;
  label?: string;
  active?: boolean;
  r?: number;
};

export function ThreadNode({
  x,
  y,
  label,
  active = false,
  r = 2.5,
}: ThreadNodeProps) {
  return (
    <g transform={`translate(${x} ${y})`} opacity={active ? 1 : 0.55}>
      <circle r={r} fill="currentColor" />
      {label ? (
        <text
          x={8}
          y={3}
          className="fill-current font-mono text-[9px] tracking-wider"
          style={{ fill: "currentColor", opacity: 0.7 }}
        >
          {label}
        </text>
      ) : null}
    </g>
  );
}

type ThreadCanvasProps = {
  children: ReactNode;
  className?: string;
  viewBox?: string;
};

export function ThreadCanvas({
  children,
  className = "",
  viewBox = "0 0 1000 560",
}: ThreadCanvasProps) {
  const id = useId();
  return (
    <svg
      viewBox={viewBox}
      className={`h-full w-full text-[var(--mk-line)] ${className}`}
      aria-hidden="true"
      role="presentation"
      data-thread-canvas={id}
    >
      {children}
    </svg>
  );
}

/** Cubic between two points — used for living research threads. */
export function threadPath(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  bend = 0.35,
): string {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const cx1 = x1 + dx * bend;
  const cy1 = y1 + dy * (1 - bend) * 0.2;
  const cx2 = x2 - dx * bend;
  const cy2 = y2 - dy * (1 - bend) * 0.2;
  return `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;
}

export function useThreadBundle(
  pairs: Array<[number, number, number, number]>,
): string[] {
  return useMemo(
    () => pairs.map(([x1, y1, x2, y2]) => threadPath(x1, y1, x2, y2)),
    [pairs],
  );
}
