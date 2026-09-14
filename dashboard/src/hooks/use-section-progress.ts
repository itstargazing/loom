"use client";

import { useEffect, useRef, useState, type RefObject } from "react";

function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

/**
 * Progress 0–1 for a pinned scroll section.
 * Only updates while the section is near the viewport, and quantizes steps
 * so off-screen scenes don't thrash React on every Lenis frame.
 */
export function useSectionProgress(ref: RefObject<HTMLElement | null>): number {
  const [progress, setProgress] = useState(0);
  const activeRef = useRef(false);
  const lastRef = useRef(-1);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const io = new IntersectionObserver(
      ([entry]) => {
        activeRef.current = Boolean(entry?.isIntersecting);
        if (!activeRef.current) return;
        // Snap once when entering
        lastRef.current = -1;
      },
      { rootMargin: "15% 0px", threshold: [0, 0.01] },
    );
    io.observe(el);

    let frame = 0;
    const STEPS = 48;

    const update = () => {
      frame = 0;
      if (!activeRef.current) return;
      const rect = el.getBoundingClientRect();
      const travel = Math.max(1, el.offsetHeight - window.innerHeight);
      const scrolled = clamp(-rect.top, 0, travel);
      const next = Math.round((scrolled / travel) * STEPS) / STEPS;
      if (next === lastRef.current) return;
      lastRef.current = next;
      setProgress(next);
    };

    const onScroll = () => {
      if (!activeRef.current) return;
      if (frame) return;
      frame = window.requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      io.disconnect();
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [ref]);

  return progress;
}

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReduced(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  return reduced;
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function mapRange(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number,
): number {
  if (inMax === inMin) return outMin;
  const t = clamp((value - inMin) / (inMax - inMin), 0, 1);
  return lerp(outMin, outMax, t);
}
