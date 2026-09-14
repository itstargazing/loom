"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

const KINDS = [
  { kind: "HIGHLIGHT", body: "deadline is March 15", meta: "selection · 2s ago" },
  { kind: "COPY", body: "GPA ≥ 3.5 required", meta: "clipboard · 5s ago" },
  { kind: "DWELL", body: "§4 Eligibility", meta: "held 18s" },
  { kind: "PAGE", body: "scholarship portal", meta: "opened" },
  { kind: "PDF", body: "forms due March 20", meta: "reader" },
  { kind: "CLAIM", body: "stipend covers housing", meta: "classified" },
] as const;

type LiveSignal = (typeof KINDS)[number] & {
  id: number;
  x: number;
  y: number;
};

/** Ambient capture stream — signals appear, pulse, and fade like real capture. */
export function SignalStream({ className = "" }: { className?: string }) {
  const reduced = useReducedMotion();
  const [items, setItems] = useState<LiveSignal[]>([]);
  const seq = useRef(0);

  useEffect(() => {
    if (reduced) {
      setItems(
        KINDS.slice(0, 4).map((s, i) => ({
          ...s,
          id: i + 1,
          x: 12 + (i % 2) * 48,
          y: 18 + Math.floor(i / 2) * 36,
        })),
      );
      return;
    }

    let alive = true;
    let kindIndex = 0;

    const spawn = () => {
      if (!alive) return;
      const base = KINDS[kindIndex % KINDS.length];
      kindIndex += 1;
      seq.current += 1;
      const next: LiveSignal = {
        ...base,
        id: seq.current,
        x: 8 + Math.random() * 62,
        y: 10 + Math.random() * 68,
      };
      setItems((prev) => [...prev.filter((p) => p.id !== next.id).slice(-5), next]);
    };

    setItems([]);
    spawn();
    const t = window.setInterval(spawn, 1600);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [reduced]);

  return (
    <div className={`relative overflow-hidden ${className}`} aria-hidden>
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(242,240,236,0.08),transparent_65%)]" />
      {items.map((item) => (
        <motion.div
          key={item.id}
          className="mk-signal absolute max-w-[14rem] border border-[var(--mk-line)] bg-[rgba(5,5,5,0.72)] px-3 py-2 backdrop-blur-[2px]"
          style={{ left: `${item.x}%`, top: `${item.y}%` }}
          initial={reduced ? false : { opacity: 0, scale: 0.92, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="flex items-center gap-2">
            <span className="mk-signal-dot" />
            <p className="font-mono text-[9px] tracking-[0.22em] text-[var(--mk-faint)]">
              {item.kind}
            </p>
          </div>
          <p className="mk-font-display mt-2 text-[13px] leading-snug tracking-tight text-[var(--mk-text)]">
            {item.body}
          </p>
          <p className="mt-1.5 font-mono text-[9px] tracking-[0.12em] text-[var(--mk-dim)]">
            {item.meta}
          </p>
        </motion.div>
      ))}
    </div>
  );
}
