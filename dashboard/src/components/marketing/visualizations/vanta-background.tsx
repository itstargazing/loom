"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { usePrefersReducedMotion } from "@/hooks/use-section-progress";

type VantaEffect = {
  destroy: () => void;
  resize?: () => void;
};

type VantaEffectName = "net" | "fog" | "waves" | "dots";

type VantaBackgroundProps = {
  effect?: VantaEffectName;
  className?: string;
  children?: ReactNode;
  dim?: boolean;
  options?: Record<string, unknown>;
};

const DEFAULTS: Record<VantaEffectName, Record<string, unknown>> = {
  net: {
    mouseControls: true,
    touchControls: true,
    gyroControls: false,
    minHeight: 200,
    minWidth: 200,
    scale: 1,
    scaleMobile: 1,
    color: 0xf2f0ec,
    backgroundColor: 0x050505,
    points: 9,
    maxDistance: 22,
    spacing: 18,
    showDots: true,
  },
  fog: {
    mouseControls: true,
    touchControls: true,
    gyroControls: false,
    minHeight: 200,
    minWidth: 200,
    highlightColor: 0xf2f0ec,
    midtoneColor: 0x2a2428,
    lowlightColor: 0x0a0a0a,
    baseColor: 0x050505,
    blurFactor: 0.55,
    speed: 0.75,
    zoom: 0.85,
  },
  waves: {
    mouseControls: true,
    touchControls: true,
    gyroControls: false,
    minHeight: 200,
    minWidth: 200,
    color: 0x0c0c0c,
    shininess: 28,
    waveHeight: 14,
    waveSpeed: 0.55,
    zoom: 0.85,
  },
  dots: {
    mouseControls: true,
    touchControls: true,
    gyroControls: false,
    minHeight: 200,
    minWidth: 200,
    color: 0xf2f0ec,
    color2: 0xf2f0ec,
    backgroundColor: 0x050505,
    size: 2.4,
    spacing: 28,
    showLines: true,
  },
};

/**
 * Vanta mounts into a dedicated behind-content layer so WebGL never covers copy.
 * https://github.com/tengbao/vanta
 */
export function VantaBackground({
  effect = "net",
  className = "",
  children,
  dim = true,
  options,
}: VantaBackgroundProps) {
  const layerRef = useRef<HTMLDivElement>(null);
  const effectRef = useRef<VantaEffect | null>(null);
  const optionsRef = useRef(options);
  const reduced = usePrefersReducedMotion();
  optionsRef.current = options;

  useEffect(() => {
    if (reduced || !layerRef.current) return;

    let cancelled = false;

    async function mount() {
      const THREE = await import("three");
      const loaders: Record<
        VantaEffectName,
        () => Promise<{ default: (opts: Record<string, unknown>) => VantaEffect }>
      > = {
        net: () => import("vanta/dist/vanta.net.min"),
        fog: () => import("vanta/dist/vanta.fog.min"),
        waves: () => import("vanta/dist/vanta.waves.min"),
        dots: () => import("vanta/dist/vanta.dots.min"),
      };

      try {
        const mod = await loaders[effect]();
        if (cancelled || !layerRef.current) return;

        const isMobile =
          window.matchMedia("(max-width: 768px), (pointer: coarse)").matches;
        const mobileTune =
          effect === "net"
            ? { points: 6, maxDistance: 18, spacing: 20 }
            : effect === "fog"
              ? { blurFactor: 0.65, speed: 0.5 }
              : {};

        effectRef.current?.destroy();
        effectRef.current = mod.default({
          el: layerRef.current,
          THREE,
          ...DEFAULTS[effect],
          ...(isMobile ? mobileTune : {}),
          ...optionsRef.current,
        });
      } catch {
        // WebGL unavailable — leave solid background
      }
    }

    void mount();

    const onResize = () => effectRef.current?.resize?.();
    window.addEventListener("resize", onResize);

    return () => {
      cancelled = true;
      window.removeEventListener("resize", onResize);
      effectRef.current?.destroy();
      effectRef.current = null;
    };
  }, [effect, reduced]);

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div
        ref={layerRef}
        className="mk-vanta pointer-events-none absolute inset-0 z-0"
        aria-hidden
      />
      {dim ? (
        <div
          className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-b from-[rgba(5,5,5,0.25)] via-[rgba(5,5,5,0.55)] to-[rgba(5,5,5,0.9)]"
          aria-hidden
        />
      ) : null}
      <div className="relative z-[2]">{children}</div>
    </div>
  );
}
