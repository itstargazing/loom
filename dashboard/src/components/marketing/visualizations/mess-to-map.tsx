"use client";

import { motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";

const FRAGMENTS = [
  { id: "a", text: "March 15 — deadline?", x: 12, y: 16 },
  { id: "b", text: "PDF says March 20", x: 72, y: 14 },
  { id: "c", text: "scholarship portal", x: 28, y: 44 },
  { id: "d", text: "copied claim · GPA", x: 68, y: 40 },
  { id: "e", text: "email draft", x: 14, y: 70 },
  { id: "f", text: "source_014", x: 78, y: 68 },
  { id: "g", text: "highlight · stipend", x: 42, y: 28 },
  { id: "h", text: "tabs: 14 open", x: 52, y: 82 },
];

/** Two-column centers with equal chip width (42%) — gap stays clear. */
const ORDERED = [
  { id: "a", text: "DEADLINE · Mar 15", x: 26, y: 16 },
  { id: "b", text: "CONFLICT · Mar 20", x: 74, y: 16 },
  { id: "c", text: "SOURCE · portal", x: 26, y: 38 },
  { id: "d", text: "CLAIM · GPA", x: 74, y: 38 },
  { id: "e", text: "READING · email", x: 26, y: 60 },
  { id: "f", text: "CITATION · 014", x: 74, y: 60 },
  { id: "g", text: "TERM · stipend", x: 26, y: 82 },
  { id: "h", text: "THREAD · synced", x: 74, y: 82 },
];

function clamp01(n: number) {
  return Math.min(1, Math.max(0, n));
}

/** Messy browsing fragments reorganize into structured memory. */
export function MessToMap() {
  const sectionRef = useRef<HTMLElement>(null);
  const [manual, setManual] = useState<number | null>(null);
  const [scrollT, setScrollT] = useState(0.15);
  const manualRef = useRef<number | null>(null);
  manualRef.current = manual;

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;

    let frame = 0;
    let last = -1;

    const update = () => {
      frame = 0;
      if (manualRef.current !== null) return;

      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      const start = vh * 0.85;
      const end = vh * 0.2;
      const raw = (start - rect.top) / (start - end + rect.height * 0.35);
      const next = Math.round(clamp01(raw) * 60) / 60;
      if (next === last) return;
      last = next;
      setScrollT(next);
    };

    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("touchmove", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      document.removeEventListener("scroll", onScroll);
      window.removeEventListener("touchmove", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  const t = manual ?? scrollT;

  const items = useMemo(
    () =>
      FRAGMENTS.map((f, i) => {
        const o = ORDERED[i];
        return {
          id: f.id,
          text: t > 0.55 ? o.text : f.text,
          x: f.x + (o.x - f.x) * t,
          y: f.y + (o.y - f.y) * t,
          structured: t > 0.55,
        };
      }),
    [t],
  );

  return (
    <section
      ref={sectionRef}
      className="relative z-0 border-t border-[var(--mk-line)] bg-[var(--mk-bg)] py-20 md:py-28"
    >
      <div className="mk-wrap grid w-full gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div className="min-w-0">
          <p className="mk-label">06 — TRANSFORM</p>
          <h2 className="mk-display mt-5 text-[clamp(2.4rem,5vw,4.2rem)]">
            See how Loom
            <br />
            changes information.
          </h2>
          <p className="mk-body mt-6">
            Scroll through this section — or drag the slider — and watch messy
            fragments settle into claims, deadlines, and sources.
          </p>
          <label className="mt-8 block max-w-sm">
            <span className="mk-label">Organization</span>
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round(t * 100)}
              onChange={(e) => setManual(Number(e.target.value) / 100)}
              className="mt-3 w-full accent-[var(--mk-accent)]"
              aria-label="Reorganize information"
            />
          </label>
          {manual !== null ? (
            <button
              type="button"
              className="mt-3 font-mono text-[10px] tracking-[0.16em] text-[var(--mk-faint)] underline-offset-2 hover:text-[var(--mk-dim)] hover:underline"
              onClick={() => setManual(null)}
            >
              BACK TO SCROLL
            </button>
          ) : null}
          <p className="mt-3 font-mono text-[11px] tracking-[0.16em] text-[var(--mk-faint)]">
            {t < 0.35 ? "CHAOS" : t < 0.7 ? "CLASSIFYING" : "STRUCTURED MEMORY"}
          </p>
        </div>

        <div
          className="mk-stage relative aspect-[5/4] w-full overflow-hidden"
          data-cursor="explore"
        >
          <div className="relative z-[1] flex h-full flex-col p-4 md:p-6">
            <div className="mb-4 flex shrink-0 items-center justify-between border-b border-[var(--mk-line)] pb-3">
              <span className="font-mono text-[10px] tracking-[0.18em] text-[var(--mk-faint)]">
                LIVE FIELD
              </span>
              <span className="inline-flex items-center gap-2 font-mono text-[10px] tracking-[0.18em] text-[var(--mk-accent)]">
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--mk-accent)]"
                  aria-hidden
                />
                {Math.round(t * 100)}%
              </span>
            </div>

            <div className="relative min-h-0 flex-1 overflow-hidden">
              {/* Lines only — no center nodes (those sat on top of labels). */}
              <svg
                className="pointer-events-none absolute inset-0 z-0 h-full w-full"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                aria-hidden
              >
                {ORDERED.slice(0, 4).map((_, i) => {
                  const a = items[i];
                  const b = items[i + 4];
                  if (!a || !b) return null;
                  return (
                    <motion.line
                      key={i}
                      x1={a.x}
                      y1={a.y}
                      x2={b.x}
                      y2={b.y}
                      stroke="rgba(242,240,236,0.28)"
                      strokeWidth={0.3}
                      initial={false}
                      animate={{ opacity: Math.max(0, (t - 0.35) * 1.4) }}
                      transition={{ duration: 0.2 }}
                    />
                  );
                })}
              </svg>

              {items.map((item) => (
                <motion.div
                  key={item.id}
                  className={[
                    // Fixed w/h so short labels (CLAIM) match long ones (CONFLICT).
                    "absolute z-[1] box-border flex h-10 w-[42%] -translate-x-1/2 -translate-y-1/2 items-center gap-2 border px-2.5 font-mono text-[10px] leading-none tracking-[0.05em] md:h-11 md:text-[11px]",
                    item.structured
                      ? "border-[var(--mk-accent)]/35 bg-[rgba(12,12,12,0.92)] text-[var(--mk-text)]"
                      : "border-[var(--mk-line)] bg-[rgba(5,5,5,0.88)] text-[var(--mk-dim)]",
                  ].join(" ")}
                  initial={false}
                  animate={{ left: `${item.x}%`, top: `${item.y}%` }}
                  transition={{ type: "spring", stiffness: 120, damping: 20 }}
                >
                  <span
                    className={[
                      "inline-block h-1.5 w-1.5 shrink-0 rounded-full",
                      item.structured
                        ? "bg-[var(--mk-accent)]"
                        : "bg-[var(--mk-faint)]",
                    ].join(" ")}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1 truncate">{item.text}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
