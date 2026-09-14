"use client";

import { useEffect, useRef, useState } from "react";

import { usePrefersReducedMotion } from "@/hooks/use-section-progress";

export function CustomCursor() {
  const reduced = usePrefersReducedMotion();
  const elRef = useRef<HTMLDivElement>(null);
  const pos = useRef({ x: 0, y: 0 });
  const target = useRef({ x: 0, y: 0 });
  const [state, setState] = useState<"default" | "hover" | "explore">("default");
  const [label, setLabel] = useState("");
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const touch = window.matchMedia("(hover: none), (pointer: coarse)").matches;
    if (touch || reduced) {
      document.documentElement.classList.add(touch ? "mk-touch" : "mk-reduced");
      return;
    }
    setEnabled(true);

    let frame = 0;
    const onMove = (e: MouseEvent) => {
      target.current = { x: e.clientX, y: e.clientY };
    };

    const onOver = (e: MouseEvent) => {
      const hit = (e.target as HTMLElement | null)?.closest?.("[data-cursor]");
      if (!hit) {
        setState("default");
        setLabel("");
        return;
      }
      const mode = hit.getAttribute("data-cursor") || "hover";
      if (mode === "explore" || mode === "view" || mode === "open") {
        setState("explore");
        setLabel(mode.toUpperCase());
      } else {
        setState("hover");
        setLabel("");
      }
    };

    const tick = () => {
      pos.current.x += (target.current.x - pos.current.x) * 0.22;
      pos.current.y += (target.current.y - pos.current.y) * 0.22;
      const el = elRef.current;
      if (el) {
        el.style.transform = `translate3d(${pos.current.x}px, ${pos.current.y}px, 0)`;
      }
      frame = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    window.addEventListener("mouseover", onOver);
    frame = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseover", onOver);
      cancelAnimationFrame(frame);
      document.documentElement.classList.remove("mk-touch", "mk-reduced");
    };
  }, [reduced]);

  if (!enabled) return null;

  return (
    <div
      ref={elRef}
      className="mk-cursor"
      data-state={state}
      aria-hidden
    >
      {state === "explore" ? label || "EXPLORE" : null}
    </div>
  );
}

export function ScrollProgress() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const p = max > 0 ? window.scrollY / max : 0;
      if (ref.current) ref.current.style.transform = `scaleX(${p})`;
    };
    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return <div ref={ref} className="mk-progress" style={{ transform: "scaleX(0)" }} aria-hidden />;
}
