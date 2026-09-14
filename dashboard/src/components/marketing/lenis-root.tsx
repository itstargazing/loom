"use client";

import { useEffect, type ReactNode } from "react";
import Lenis from "lenis";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "lenis/dist/lenis.css";

import { usePrefersReducedMotion } from "@/hooks/use-section-progress";

gsap.registerPlugin(ScrollTrigger);

function isTouchDevice() {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(hover: none), (pointer: coarse)").matches ||
    navigator.maxTouchPoints > 0
  );
}

/** Lenis on desktop only — native scroll on mobile so IO / motion fire reliably. */
export function LenisRoot({ children }: { children: ReactNode }) {
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    document.documentElement.classList.add("marketing-active");
    const touch = isTouchDevice();
    if (touch) document.documentElement.classList.add("mk-touch");

    if (reduced) {
      document.documentElement.classList.add("mk-reduced");
      return () => {
        document.documentElement.classList.remove(
          "marketing-active",
          "mk-reduced",
          "mk-touch",
        );
      };
    }

    // Native touch scrolling — Lenis often breaks Framer whileInView on phones
    if (touch) {
      ScrollTrigger.refresh();
      const refresh = () => ScrollTrigger.refresh();
      window.addEventListener("resize", refresh);
      window.addEventListener("orientationchange", refresh);
      return () => {
        document.documentElement.classList.remove(
          "marketing-active",
          "mk-reduced",
          "mk-touch",
        );
        window.removeEventListener("resize", refresh);
        window.removeEventListener("orientationchange", refresh);
      };
    }

    const lenis = new Lenis({
      autoRaf: true,
      anchors: true,
      duration: 1.2,
      easing: (t: number) => Math.min(1, 1.001 - 2 ** (-10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.5,
    });

    lenis.on("scroll", () => {
      ScrollTrigger.update();
      window.dispatchEvent(new Event("scroll"));
    });

    const refresh = () => ScrollTrigger.refresh();
    window.addEventListener("resize", refresh);
    requestAnimationFrame(() => ScrollTrigger.refresh());

    return () => {
      document.documentElement.classList.remove(
        "marketing-active",
        "mk-reduced",
        "mk-touch",
      );
      window.removeEventListener("resize", refresh);
      lenis.destroy();
      ScrollTrigger.getAll().forEach((t) => t.kill());
    };
  }, [reduced]);

  return children;
}
