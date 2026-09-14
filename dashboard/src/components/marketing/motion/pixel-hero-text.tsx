"use client";

import { useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";

const POOL = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz";

function pick(seed: number) {
  return POOL[seed % POOL.length]!;
}

/**
 * Light decode for the hero headline only — short, subtle, no layout thrash.
 */
export function PixelHeroText({
  text,
  className = "",
}: {
  text: string;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const rootRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const lineEls = Array.from(
      root.querySelectorAll<HTMLElement>("[data-pixel-line]"),
    );
    const targets = text.split("\n");

    if (reduced) {
      lineEls.forEach((el, i) => {
        el.textContent = targets[i] || "\u00A0";
      });
      root.classList.remove("mk-pixel-hero--live");
      return;
    }

    root.classList.add("mk-pixel-hero--live");

    let frame = 0;
    const frames = 14;
    let raf = 0;
    let last = 0;

    const tick = (now: number) => {
      // ~16fps — enough for decode, cheap on main thread
      if (now - last < 60) {
        raf = requestAnimationFrame(tick);
        return;
      }
      last = now;
      frame += 1;

      const t = Math.min(1, frame / frames);
      // ease-out so most letters settle early
      const settled = t * t * (3 - 2 * t);

      lineEls.forEach((el, li) => {
        const target = targets[li] || "";
        const keep = Math.floor(target.length * settled);
        let out = "";
        for (let i = 0; i < target.length; i++) {
          const ch = target[i]!;
          if (ch === " " || ch === "'" || i < keep) {
            out += ch;
          } else {
            out += pick(frame * 11 + i * 3 + li * 5);
          }
        }
        el.textContent = out || "\u00A0";
      });

      if (frame < frames) {
        raf = requestAnimationFrame(tick);
      } else {
        lineEls.forEach((el, i) => {
          el.textContent = targets[i] || "\u00A0";
        });
        root.classList.remove("mk-pixel-hero--live");
      }
    };

    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      root.classList.remove("mk-pixel-hero--live");
    };
  }, [reduced, text]);

  const lines = text.split("\n");

  return (
    <h1
      ref={rootRef}
      className={["mk-pixel-hero", className].filter(Boolean).join(" ")}
      aria-label={text.replace(/\n/g, " ")}
    >
      {lines.map((line, i) => (
        <span key={i} data-pixel-line className="block">
          {line || "\u00A0"}
        </span>
      ))}
    </h1>
  );
}
