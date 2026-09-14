"use client";

import {
  motion,
  useReducedMotion,
  type HTMLMotionProps,
} from "framer-motion";
import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";

/** Mobile-friendly: fire as soon as any part enters the viewport */
const VIEWPORT = { once: true, amount: 0.05, margin: "0px 0px 0px 0px" } as const;

export function FadeUp({
  children,
  className = "",
  delay = 0,
  y = 28,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={VIEWPORT}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay }}
    >
      {children}
    </motion.div>
  );
}

export function RevealText({
  text,
  className = "",
  as: Tag = "h1",
  delay = 0,
}: {
  text: string;
  className?: string;
  as?: "h1" | "h2" | "h3" | "p";
  delay?: number;
}) {
  const reduced = useReducedMotion();
  const lines = text.split("\n");
  const MotionTag = motion[Tag];

  return (
    <MotionTag
      className={className}
      aria-label={text.replace(/\n/g, " ")}
      initial="hidden"
      whileInView="show"
      viewport={VIEWPORT}
    >
      {lines.map((line, i) => (
        <span key={`${line}-${i}`} className="block overflow-hidden pb-[0.08em]">
          <motion.span
            className="block will-change-transform"
            variants={{
              hidden: reduced ? { y: "0%" } : { y: "110%" },
              show: { y: "0%" },
            }}
            transition={{
              duration: 0.85,
              ease: [0.22, 1, 0.36, 1],
              delay: delay + i * 0.08,
            }}
          >
            {line || "\u00A0"}
          </motion.span>
        </span>
      ))}
    </MotionTag>
  );
}

export function MagneticButton({
  children,
  className = "",
  strength = 0.28,
  ...props
}: HTMLMotionProps<"a"> & { strength?: number }) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLAnchorElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (reduced) return;
    // Skip magnetic on touch — no cursor
    if (window.matchMedia("(hover: none), (pointer: coarse)").matches) return;

    const el = ref.current;
    if (!el) return;

    const onMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      const x = e.clientX - (rect.left + rect.width / 2);
      const y = e.clientY - (rect.top + rect.height / 2);
      setOffset({ x: x * strength, y: y * strength });
    };
    const onLeave = () => setOffset({ x: 0, y: 0 });

    el.addEventListener("mousemove", onMove);
    el.addEventListener("mouseleave", onLeave);
    return () => {
      el.removeEventListener("mousemove", onMove);
      el.removeEventListener("mouseleave", onLeave);
    };
  }, [reduced, strength]);

  return (
    <motion.a
      ref={ref}
      className={className}
      style={{ x: offset.x, y: offset.y }}
      transition={{ type: "spring", stiffness: 320, damping: 22, mass: 0.4 }}
      data-cursor="hover"
      {...props}
    >
      {children}
    </motion.a>
  );
}

export function NumberCounter({
  value,
  suffix = "",
  className = "",
}: {
  value: number;
  suffix?: string;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const [n, setN] = useState(reduced ? value : 0);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const run = () => {
      if (started.current) return;
      started.current = true;
      if (reduced) {
        setN(value);
        return;
      }
      const start = performance.now();
      const duration = 1100;
      let frame = 0;
      const tick = (now: number) => {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - (1 - t) ** 3;
        setN(Math.round(value * eased));
        if (t < 1) frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(frame);
    };

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) run();
      },
      { threshold: 0.05, rootMargin: "0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduced, value]);

  return (
    <span ref={ref} className={className}>
      {n}
      {suffix}
    </span>
  );
}

export function usePinnedProgress(ref: RefObject<HTMLElement | null>): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let frame = 0;
    let last = -1;
    let visible = false;
    const STEPS = 60;
    const clamp = (n: number, min: number, max: number) =>
      Math.min(max, Math.max(min, n));

    const update = () => {
      frame = 0;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      visible = rect.bottom > 0 && rect.top < vh;
      if (!visible) return;

      const travel = Math.max(1, el.offsetHeight - vh);
      const scrolled = clamp(-rect.top, 0, travel);
      const next = Math.round((scrolled / travel) * STEPS) / STEPS;
      if (next === last) return;
      last = next;
      setProgress(next);
    };

    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(update);
    };

    const io = new IntersectionObserver(
      ([entry]) => {
        visible = Boolean(entry?.isIntersecting);
        if (visible) {
          last = -1;
          onScroll();
        }
      },
      { rootMargin: "40% 0px", threshold: [0, 0.01, 0.1, 0.5] },
    );
    io.observe(el);

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    document.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("touchmove", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      io.disconnect();
      window.removeEventListener("scroll", onScroll);
      document.removeEventListener("scroll", onScroll);
      window.removeEventListener("touchmove", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [ref]);

  return progress;
}
