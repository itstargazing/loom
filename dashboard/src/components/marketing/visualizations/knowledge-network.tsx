"use client";

import { useEffect, useRef } from "react";

import { usePrefersReducedMotion } from "@/hooks/use-section-progress";

type Node = {
  id: number;
  x: number;
  y: number;
  ox: number;
  oy: number;
  r: number;
  phase: number;
  speed: number;
  label?: string;
  kind: number;
};

type Edge = { a: number; b: number; accent: boolean };

type Packet = {
  edge: number;
  t: number;
  speed: number;
  accent: boolean;
};

const LABELS = [
  "deadline",
  "claim",
  "source",
  "term",
  "pdf",
  "quote",
  "job",
  "flag",
  "highlight",
  "dwell",
];

function buildGraph(seed: number, count = 26): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  for (let i = 0; i < count; i++) {
    const a = ((i * 137.508 + seed) % 360) * (Math.PI / 180);
    const rad = 16 + ((i * 19) % 34);
    const x = 50 + Math.cos(a) * rad + ((i % 5) - 2) * 1.1;
    const y = 50 + Math.sin(a) * rad * 0.7 + ((i % 7) - 3) * 1.05;
    nodes.push({
      id: i,
      x,
      y,
      ox: x,
      oy: y,
      r: 0.9 + (i % 4) * 0.28,
      phase: (i * 0.73) % (Math.PI * 2),
      speed: 0.35 + (i % 5) * 0.08,
      label: i % 3 === 0 ? LABELS[i % LABELS.length] : undefined,
      kind: i % 5,
    });
  }

  const edges: Edge[] = [];
  for (let i = 0; i < count; i++) {
    const b = (i * 5 + 7) % count;
    const c = (i * 3 + 11) % count;
    if (b !== i) edges.push({ a: i, b, accent: i % 4 === 0 });
    if (c !== i && c !== b) edges.push({ a: i, b: c, accent: i % 6 === 0 });
  }
  return { nodes, edges };
}

function clamp01(n: number) {
  return Math.min(1, Math.max(0, n));
}

/** Live knowledge network — pulses, packets, drift. */
export function KnowledgeNetwork({
  progress = 0.55,
  interactive = true,
  className = "",
}: {
  progress?: number;
  interactive?: boolean;
  className?: string;
}) {
  const reduced = usePrefersReducedMotion();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const progressRef = useRef(progress);
  progressRef.current = progress;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { nodes, edges } = buildGraph(11);
    const packets: Packet[] = [];
    let pointer = { x: 50, y: 50, active: false };
    let raf = 0;
    let last = performance.now();
    let spawnAcc = 0;
    let ping = { x: 50, y: 50, life: 0 };
    let visible = true;
    let tick: (now: number) => void = () => undefined;

    const io = new IntersectionObserver(
      ([entry]) => {
        const was = visible;
        visible = Boolean(entry?.isIntersecting);
        if (visible && !was && !reduced) {
          last = performance.now();
          raf = requestAnimationFrame(tick);
        }
      },
      { threshold: 0.05 },
    );
    io.observe(canvas);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const cssW = Math.max(1, Math.floor(rect.width));
      const cssH = Math.max(1, Math.floor(rect.height));
      canvas.width = Math.max(1, Math.floor(cssW * dpr));
      canvas.height = Math.max(1, Math.floor(cssH * dpr));
      canvas.style.width = `${cssW}px`;
      canvas.style.height = `${cssH}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    const ro =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => {
            resize();
            if (!reduced && visible) {
              last = performance.now();
              cancelAnimationFrame(raf);
              raf = requestAnimationFrame(tick);
            }
          })
        : null;
    ro?.observe(canvas.parentElement || canvas);

    const onMove = (e: PointerEvent) => {
      if (!interactive) return;
      const rect = canvas.getBoundingClientRect();
      pointer = {
        x: ((e.clientX - rect.left) / rect.width) * 100,
        y: ((e.clientY - rect.top) / rect.height) * 100,
        active: true,
      };
    };
    const onLeave = () => {
      pointer = { ...pointer, active: false };
    };

    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerleave", onLeave);
    window.addEventListener("resize", resize);

    const toXY = (nx: number, ny: number, w: number, h: number) => {
      // Keep graph fully inside the stage without changing stage size
      const pad = 0.07;
      return {
        x: (pad + (nx / 100) * (1 - 2 * pad)) * w,
        y: (pad + (ny / 100) * (1 - 2 * pad)) * h,
      };
    };

    const drawStatic = () => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);
      const p = reduced ? 0.75 : progressRef.current;
      const organized = clamp01((p - 0.3) / 0.5);
      const edgeCount = Math.floor(p * edges.length);

      const glow = ctx.createRadialGradient(w * 0.5, h * 0.5, 0, w * 0.5, h * 0.5, w * 0.45);
      glow.addColorStop(0, "rgba(242,240,236,0.14)");
      glow.addColorStop(1, "rgba(242,240,236,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      for (let i = 0; i < edgeCount; i++) {
        const e = edges[i];
        const na = nodes[e.a];
        const nb = nodes[e.b];
        const ax = na.ox + (50 - na.ox) * organized * 0.2;
        const ay = na.oy + (50 - na.oy) * organized * 0.2;
        const bx = nb.ox + (50 - nb.ox) * organized * 0.2;
        const by = nb.oy + (50 - nb.oy) * organized * 0.2;
        const a = toXY(ax, ay, w, h);
        const b = toXY(bx, by, w, h);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = e.accent
          ? "rgba(242,240,236,0.4)"
          : "rgba(242,240,236,0.16)";
        ctx.lineWidth = e.accent ? 1.1 : 0.7;
        ctx.stroke();
      }

      nodes.forEach((n, i) => {
        const active = p > i / nodes.length;
        const x = n.ox + (50 - n.ox) * organized * 0.22;
        const y = n.oy + (50 - n.oy) * organized * 0.22;
        const pt = toXY(x, y, w, h);
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, n.r * (active ? 2.2 : 1.2), 0, Math.PI * 2);
        ctx.fillStyle = active
          ? "rgba(242,240,236,0.9)"
          : "rgba(242,240,236,0.25)";
        ctx.fill();
      });
    };

    if (reduced) {
      drawStatic();
      return () => {
        io.disconnect();
        ro?.disconnect();
        canvas.removeEventListener("pointermove", onMove);
        canvas.removeEventListener("pointerleave", onLeave);
        window.removeEventListener("resize", resize);
      };
    }

    tick = (now: number) => {
      if (!visible) return;
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const p = progressRef.current;
      const organized = clamp01((p - 0.3) / 0.5);
      const edgeCount = Math.max(1, Math.floor(p * edges.length));

      ctx.clearRect(0, 0, w, h);

      // ambient glow
      const glow = ctx.createRadialGradient(w * 0.5, h * 0.48, 0, w * 0.5, h * 0.48, w * 0.48);
      glow.addColorStop(0, `rgba(242,240,236,${0.1 + organized * 0.1})`);
      glow.addColorStop(1, "rgba(242,240,236,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      // node drift + pointer attraction
      for (const n of nodes) {
        n.phase += dt * n.speed;
        const driftX = Math.cos(n.phase) * 0.55;
        const driftY = Math.sin(n.phase * 1.15) * 0.45;
        let tx = n.ox + driftX + (50 - n.ox) * organized * 0.2;
        let ty = n.oy + driftY + (50 - n.oy) * organized * 0.2;
        if (pointer.active) {
          const dx = pointer.x - tx;
          const dy = pointer.y - ty;
          const dist = Math.hypot(dx, dy) || 1;
          if (dist < 28) {
            const force = ((28 - dist) / 28) * 2.2;
            tx += (dx / dist) * force;
            ty += (dy / dist) * force;
          }
        }
        n.x += (tx - n.x) * 0.08;
        n.y += (ty - n.y) * 0.08;
      }

      // edges
      for (let i = 0; i < edgeCount; i++) {
        const e = edges[i];
        const na = nodes[e.a];
        const nb = nodes[e.b];
        const a = toXY(na.x, na.y, w, h);
        const b = toXY(nb.x, nb.y, w, h);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = e.accent
          ? "rgba(242,240,236,0.38)"
          : "rgba(242,240,236,0.14)";
        ctx.lineWidth = e.accent ? 1.15 : 0.75;
        ctx.stroke();
      }

      // spawn traveling signal packets
      spawnAcc += dt;
      const spawnEvery = 0.22 - organized * 0.08;
      while (spawnAcc > spawnEvery) {
        spawnAcc -= spawnEvery;
        const edge = Math.floor(Math.random() * edgeCount);
        packets.push({
          edge,
          t: 0,
          speed: 0.35 + Math.random() * 0.55,
          accent: edges[edge]?.accent || Math.random() > 0.7,
        });
        if (packets.length > 28) packets.shift();
      }

      for (let i = packets.length - 1; i >= 0; i--) {
        const pkt = packets[i];
        pkt.t += dt * pkt.speed;
        if (pkt.t >= 1) {
          const e = edges[pkt.edge];
          if (e) {
            const n = nodes[e.b];
            ping = { x: n.x, y: n.y, life: 1 };
          }
          packets.splice(i, 1);
          continue;
        }
        const e = edges[pkt.edge];
        if (!e) continue;
        const na = nodes[e.a];
        const nb = nodes[e.b];
        const x = na.x + (nb.x - na.x) * pkt.t;
        const y = na.y + (nb.y - na.y) * pkt.t;
        const pt = toXY(x, y, w, h);

        // soft trail
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, pkt.accent ? 3.2 : 2.2, 0, Math.PI * 2);
        ctx.fillStyle = pkt.accent
          ? "rgba(242,240,236,0.22)"
          : "rgba(242,240,236,0.12)";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(pt.x, pt.y, pkt.accent ? 1.6 : 1.15, 0, Math.PI * 2);
        ctx.fillStyle = pkt.accent
          ? "rgba(242,240,236,0.95)"
          : "rgba(242,240,236,0.85)";
        ctx.fill();
      }

      // arrival ping
      if (ping.life > 0) {
        ping.life -= dt * 1.6;
        const pt = toXY(ping.x, ping.y, w, h);
        const r = (1 - ping.life) * 18;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, Math.max(0.1, r), 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(242,240,236,${Math.max(0, ping.life) * 0.55})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // nodes
      nodes.forEach((n, i) => {
        const active = p > i / nodes.length * 0.92;
        const pt = toXY(n.x, n.y, w, h);
        const pulse = 1 + Math.sin(n.phase * 2.2) * 0.18;
        const radius = n.r * (active ? 2.4 : 1.25) * pulse;

        if (active) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, radius * 2.8, 0, Math.PI * 2);
          ctx.fillStyle =
            n.kind === 0
              ? "rgba(242,240,236,0.12)"
              : "rgba(242,240,236,0.06)";
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = active
          ? n.kind === 0
            ? "rgba(242,240,236,0.95)"
            : "rgba(242,240,236,0.92)"
          : "rgba(242,240,236,0.22)";
        ctx.fill();

        if (n.label && active && organized > 0.25) {
          ctx.font = "10px ui-monospace, monospace";
          ctx.fillStyle = "rgba(154,152,143,0.85)";
          ctx.textAlign = "center";
          ctx.fillText(n.label, pt.x, pt.y - radius - 6);
        }
      });

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      ro?.disconnect();
      canvas.removeEventListener("pointermove", onMove);
      canvas.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("resize", resize);
    };
  }, [interactive, reduced]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      role="img"
      aria-label="Animated knowledge network with traveling signals"
      data-cursor="explore"
      style={{ display: "block", width: "100%", height: "100%" }}
    />
  );
}
