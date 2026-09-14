"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

import {
  FadeUp,
  MagneticButton,
  NumberCounter,
  RevealText,
  usePinnedProgress,
} from "../motion/primitives";
import { PixelHeroText } from "../motion/pixel-hero-text";
import { KnowledgeNetwork } from "../visualizations/knowledge-network";
import { SignalStream } from "../visualizations/signal-stream";
import { VantaBackground } from "../visualizations/vanta-background";

export function SiteHero() {
  return (
    <section id="product" className="relative min-h-[100svh] overflow-hidden">
      <VantaBackground
        effect="net"
        className="absolute inset-0 min-h-[100svh]"
        options={{ points: 10, maxDistance: 24, spacing: 17 }}
      >
        <div className="flex min-h-[100svh] items-end pb-16 pt-28 md:items-center md:pb-24 md:pt-24">
          <div className="mk-wrap relative z-10 grid w-full gap-12 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
            <div>
              <FadeUp>
                <p className="mk-label">LOOM — LEARNING INFRASTRUCTURE</p>
              </FadeUp>
              <PixelHeroText
                text={"Your brain\ndoesn't learn\nlike a textbook."}
                className="mk-display mt-7 text-[clamp(3rem,9vw,7.2rem)]"
              />
              <FadeUp delay={0.35}>
                <p className="mk-body mt-8 max-w-xl text-base md:text-lg">
                  LOOM is the memory layer for your browser — ambient capture,
                  structured documents, and answers grounded in what you actually
                  read.
                </p>
              </FadeUp>
              <FadeUp delay={0.45}>
                <div className="mt-10 flex flex-wrap items-center gap-3">
                  <MagneticButton href="/sign-up" className="mk-btn mk-btn-primary">
                    Enter Loom →
                  </MagneticButton>
                  <MagneticButton href="#how" className="mk-btn mk-btn-ghost" strength={0.18}>
                    See the system
                  </MagneticButton>
                </div>
              </FadeUp>
              <FadeUp delay={0.55}>
                <p className="mt-8 font-mono text-[11px] tracking-[0.16em] text-[var(--mk-faint)]">
                  CAPTURE · CLASSIFY · ROUTE · ASK
                </p>
              </FadeUp>
            </div>

            <FadeUp delay={0.25} className="hidden lg:block">
              <HeroProductMini />
            </FadeUp>
          </div>
        </div>
      </VantaBackground>
    </section>
  );
}

function HeroProductMini() {
  return (
    <div className="mk-stage p-5" data-cursor="view">
      <div className="mb-5 flex items-center justify-between border-b border-[var(--mk-line)] pb-4">
        <div className="flex items-center gap-3">
          <Image
            src="/brand/loom-mark-flat.png?v=horn-1"
            alt=""
            width={36}
            height={27}
            className="h-6 w-auto"
            unoptimized
          />
          <span className="mk-font-display text-sm font-semibold tracking-tight">
            LOOM
          </span>
        </div>
        <span className="font-mono text-[10px] tracking-[0.18em] text-[var(--mk-accent)]">
          ASK · LIVE
        </span>
      </div>
      <p className="font-mono text-[10px] tracking-[0.18em] text-[var(--mk-faint)]">
        QUERY
      </p>
      <p className="mk-font-display mt-3 text-xl tracking-tight md:text-2xl">
        What did I find about scholarship deadlines?
      </p>
      <div className="mt-6 grid gap-4 border-t border-[var(--mk-line)] pt-4">
        <p className="text-sm leading-relaxed text-[var(--mk-dim)]">
          Three sources. Two list March 15. One PDF lists March 20.
        </p>
        <ul className="space-y-2">
          {[
            ["SOURCE_014", "March 15"],
            ["PDF_CLAIM", "March 20"],
            ["PORTAL", "March 15"],
          ].map(([k, v]) => (
            <li
              key={k}
              className="flex items-center justify-between font-mono text-[11px] tracking-[0.12em] text-[var(--mk-faint)]"
            >
              <span>{k}</span>
              <span className="text-[var(--mk-text)]">{v}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function SiteProblem() {
  const ref = useRef<HTMLDivElement>(null);
  const progress = usePinnedProgress(ref);
  const morph = Math.min(1, Math.max(0, (progress - 0.15) / 0.55));

  return (
    <section className="border-t border-[var(--mk-line)]">
      <div ref={ref} className="relative h-[160vh]">
        <div className="sticky top-0 z-0 flex min-h-[100vh] items-center bg-[var(--mk-bg)] py-20">
          <div className="mk-wrap">
            <p className="mk-label">01 — THE PROBLEM</p>
            <h2 className="mk-display mt-6 max-w-5xl text-[clamp(2.6rem,7vw,5.8rem)]">
              Most learning software
              <br />
              was designed around
              <br />
              <span className="relative inline-block min-h-[1.05em] min-w-[9ch]">
                <span
                  className="absolute inset-0 text-[var(--mk-faint)] transition-[opacity,transform] duration-300 ease-out"
                  style={{
                    opacity: 1 - morph,
                    transform: `translateY(${morph * -18}px)`,
                  }}
                >
                  content.
                </span>
                <span
                  className="inline-block text-[var(--mk-accent)] transition-[opacity,transform] duration-300 ease-out"
                  style={{
                    opacity: morph,
                    transform: `translateY(${(1 - morph) * 18}px)`,
                  }}
                >
                  cognition.
                </span>
              </span>
            </h2>
            <p className="mk-body mt-10 text-base md:text-lg">
              Tabs accumulate. Highlights vanish. PDFs contradict each other.
              Your serious work leaves useful residue everywhere — and almost
              nothing keeps it.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

const PIPELINE = [
  { id: "01", title: "CAPTURE", copy: "Highlights, copies, dwell, pages — ambient, not manual." },
  { id: "02", title: "CLASSIFY", copy: "Events become terms, claims, deadlines, citations." },
  { id: "03", title: "CONNECT", copy: "Duplicates merge. Contradictions surface. Threads form." },
  { id: "04", title: "FOCUS", copy: "Ask against your own trail — answers with sources." },
  { id: "05", title: "CREATE", copy: "Running documents stay current as you browse." },
];

export function SiteConcept() {
  const ref = useRef<HTMLDivElement>(null);
  const progress = usePinnedProgress(ref);

  return (
    <section id="how" className="border-t border-[var(--mk-line)]">
      <div ref={ref} className="relative h-[220vh]">
        <div className="sticky top-0 z-0 flex min-h-[100vh] items-center bg-[var(--mk-bg)] py-16">
          <div className="mk-wrap w-full">
            <p className="mk-label">02 — LOOM</p>
            <h2 className="mk-display mt-5 max-w-4xl text-[clamp(2.4rem,5.5vw,4.6rem)]">
              An interface between
              <br />
              your brain and
              <br />
              the information.
            </h2>

            <div className="mt-14 overflow-x-auto pb-4">
              <div className="flex min-w-[720px] items-stretch gap-0 md:min-w-0 md:grid md:grid-cols-5">
                {PIPELINE.map((step, i) => {
                  const active = progress > i / PIPELINE.length;
                  return (
                    <div key={step.id} className="relative flex-1 border-t border-[var(--mk-line)] pt-6 pr-4">
                      <div
                        className="absolute left-0 top-0 h-px bg-[var(--mk-accent)] transition-all duration-500"
                        style={{ width: active ? "100%" : "0%" }}
                      />
                      <p className="font-mono text-[11px] tracking-[0.2em] text-[var(--mk-faint)]">
                        {step.id}
                      </p>
                      <h3
                        className="mk-font-display mt-3 text-xl tracking-tight transition-colors duration-300 md:text-2xl"
                        style={{ color: active ? "var(--mk-text)" : "var(--mk-faint)" }}
                      >
                        {step.title}
                      </h3>
                      <p className="mt-3 text-sm leading-relaxed text-[var(--mk-dim)]">
                        {step.copy}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            <svg
              className="mt-10 hidden h-8 w-full text-[var(--mk-accent)] md:block"
              viewBox="0 0 1000 20"
              preserveAspectRatio="none"
              aria-hidden
            >
              <line
                x1="0"
                y1="10"
                x2={Math.max(40, progress * 1000)}
                y2="10"
                stroke="currentColor"
                strokeWidth="1"
              />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SiteProduct() {
  const ref = useRef<HTMLDivElement>(null);
  const progress = usePinnedProgress(ref);
  const scale = 0.92 + Math.min(1, progress * 1.4) * 0.08;

  return (
    <section className="border-t border-[var(--mk-line)]">
      <div ref={ref} className="relative h-[180vh]">
        <div className="sticky top-0 z-0 flex min-h-[100vh] items-center bg-[var(--mk-bg)] py-16">
          <div className="mk-wrap w-full">
            <p className="mk-label">03 — PRODUCT</p>
            <h2 className="mk-display mt-5 max-w-3xl text-[clamp(2.2rem,4.5vw,3.8rem)]">
              An operating environment
              <br />
              for what you already read.
            </h2>

            <div
              className="mk-stage mt-12 overflow-hidden"
              style={{
                transform: `scale(${scale})`,
                transformOrigin: "center top",
              }}
              data-cursor="view"
            >
              <div className="grid md:grid-cols-[220px_1fr]">
                <aside className="border-b border-[var(--mk-line)] p-5 md:border-b-0 md:border-r">
                  <p className="font-mono text-[10px] tracking-[0.18em] text-[var(--mk-faint)]">
                    DOCUMENTS
                  </p>
                  <ul className="mt-4 space-y-3 text-sm text-[var(--mk-dim)]">
                    {["Glossary", "Citations", "Deadlines", "Contradictions", "Reading"].map(
                      (item, i) => (
                        <li
                          key={item}
                          className={i === 3 ? "text-[var(--mk-text)]" : undefined}
                        >
                          {i === 3 ? "→ " : ""}
                          {item}
                        </li>
                      ),
                    )}
                  </ul>
                </aside>
                <div className="p-5 md:p-8">
                  <div className="flex items-center justify-between border-b border-[var(--mk-line)] pb-4">
                    <h3 className="mk-font-display text-2xl tracking-tight">
                      Contradictions
                    </h3>
                    <span className="font-mono text-[10px] tracking-[0.16em] text-[var(--mk-accent)]">
                      2 OPEN
                    </span>
                  </div>
                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <div className="border border-[var(--mk-line)] p-4">
                      <p className="font-mono text-[10px] tracking-[0.16em] text-[var(--mk-faint)]">
                        CLAIM A · SOURCE_014
                      </p>
                      <p className="mt-3 text-sm leading-relaxed text-[var(--mk-dim)]">
                        Application deadline is March 15.
                      </p>
                    </div>
                    <div className="border border-[var(--mk-line)] p-4">
                      <p className="font-mono text-[10px] tracking-[0.16em] text-[var(--mk-faint)]">
                        CLAIM B · PDF_PACK
                      </p>
                      <p className="mt-3 text-sm leading-relaxed text-[var(--mk-dim)]">
                        Forms must be received by March 20.
                      </p>
                    </div>
                  </div>
                  <p className="mt-6 max-w-2xl text-sm leading-relaxed text-[var(--mk-dim)]">
                    Same topic. Different dates. LOOM keeps both claims and
                    the browsing moments that produced them — so you can
                    resolve the conflict instead of rediscovering it.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const FEATURES = [
  {
    n: "01",
    title: "AMBIENT CAPTURE",
    line: "Highlights, copies, dwell, and pages become signals without a save ritual.",
    detail: "Five independent signals. Toggleable. Cheap on every page.",
  },
  {
    n: "02",
    title: "STRICT CLASSIFICATION",
    line: "Events become glossary terms, citations, deadlines, claims, jobs, flags.",
    detail: "Structured JSON in. Server validation out. No vibes-only taxonomy.",
  },
  {
    n: "03",
    title: "CONTRADICTION ENGINE",
    line: "Conflicting claims from different sources get promoted into open issues.",
    detail: "Topic clusters → paired claims → durable contradiction rows.",
  },
  {
    n: "04",
    title: "ASK YOUR TRAIL",
    line: "Query the memory layer and get answers grounded in what you actually saw.",
    detail: "Evidence first. Sources attached. No floating chatbot fog.",
  },
  {
    n: "05",
    title: "RESEARCH THREADS",
    line: "Running documents stay current as browsing continues.",
    detail: "Dedup keys, occurrences, confidence — memory that compounds.",
  },
  {
    n: "06",
    title: "PRIVACY BY DESIGN",
    line: "You choose what is captured. Sync is durable. Purge is intentional.",
    detail: "Capture history can go without silently erasing structured output.",
  },
];

export function SiteFeatures() {
  const ref = useRef<HTMLDivElement>(null);
  const progress = usePinnedProgress(ref);
  const index = Math.min(
    FEATURES.length - 1,
    Math.floor(progress * FEATURES.length),
  );
  const feature = FEATURES[index];

  return (
    <section id="research" className="border-t border-[var(--mk-line)]">
      <div ref={ref} className="relative h-[320vh]">
        <div className="sticky top-0 z-0 flex min-h-[100vh] items-center bg-[var(--mk-bg)] py-16">
          <div className="mk-wrap grid w-full gap-12 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div>
              <p className="mk-label">04 — CAPABILITIES</p>
              <p className="mt-6 font-mono text-[11px] tracking-[0.22em] text-[var(--mk-accent)]">
                {feature.n}
              </p>
              <h2 className="mk-display mt-4 text-[clamp(2.2rem,5vw,4rem)]">
                {feature.title}
              </h2>
              <p className="mk-body mt-6 text-base md:text-lg">{feature.line}</p>
              <p className="mt-6 font-mono text-[11px] leading-relaxed tracking-[0.08em] text-[var(--mk-faint)]">
                {feature.detail}
              </p>
              <div className="mt-10 flex gap-2">
                {FEATURES.map((f, i) => (
                  <span
                    key={f.n}
                    className="h-px w-8 transition-colors duration-300"
                    style={{
                      background:
                        i === index ? "var(--mk-accent)" : "var(--mk-line)",
                    }}
                  />
                ))}
              </div>
            </div>

            <div className="mk-stage relative aspect-[5/4] overflow-hidden p-6 md:p-8">
              {index === 0 ? (
                <SignalStream className="absolute inset-0 h-full w-full" />
              ) : (
                <KnowledgeNetwork
                  progress={0.25 + (index / (FEATURES.length - 1)) * 0.7}
                  interactive={false}
                  className="absolute inset-0 h-full w-full opacity-90"
                />
              )}
              <div className="pointer-events-none relative z-10 flex h-full flex-col justify-between">
                <p className="font-mono text-[10px] tracking-[0.18em] text-[var(--mk-faint)]">
                  SYSTEM STATE / {feature.n}
                </p>
                <div>
                  <p className="mk-font-display text-4xl tracking-tight md:text-5xl">
                    <NumberCounter value={14 + index * 11} />
                    <span className="text-[var(--mk-faint)]"> ·</span>
                  </p>
                  <p className="mt-2 font-mono text-[11px] tracking-[0.16em] text-[var(--mk-dim)]">
                    {index === 0 ? "LIVE CAPTURE FEED" : "SIGNALS IN MEMORY"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function SiteNetworkStory() {
  const ref = useRef<HTMLElement>(null);
  const [progress, setProgress] = useState(0.2);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let frame = 0;
    let last = -1;

    const update = () => {
      frame = 0;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight || 1;
      const start = vh * 0.9;
      const end = vh * 0.15;
      const raw = (start - rect.top) / Math.max(1, start - end + rect.height * 0.25);
      const next = Math.round(Math.min(1, Math.max(0, raw)) * 60) / 60;
      if (next === last) return;
      last = next;
      setProgress(next);
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

  return (
    <section
      ref={ref}
      className="relative z-0 border-t border-[var(--mk-line)] bg-[var(--mk-bg)] py-20 md:py-28"
    >
      <div className="mk-wrap grid w-full gap-10 lg:grid-cols-2 lg:items-center">
        <div>
          <p className="mk-label">05 — MEMORY GRAPH</p>
          <h2 className="mk-display mt-5 text-[clamp(2.2rem,5vw,4rem)]">
            Scattered signals
            <br />
            become a network.
          </h2>
          <p className="mk-body mt-6">
            First: disconnected fragments. Then: edges. Then: clusters that
            behave like understanding — not a folder of screenshots.
          </p>
        </div>
        <div className="mk-stage relative aspect-square w-full overflow-hidden">
          <KnowledgeNetwork
            progress={0.2 + progress * 0.8}
            className="absolute inset-0 h-full w-full"
          />
        </div>
      </div>
    </section>
  );
}

export function SiteEditorial() {
  return (
    <section
      id="about"
      className="relative z-20 border-t border-[var(--mk-line)] bg-[var(--mk-bg)] py-28 md:py-40"
    >
      <div className="mk-wrap overflow-visible">
        <FadeUp>
          <p className="mk-label">07 — MADE FOR YOUR BRAIN</p>
        </FadeUp>
        <div className="relative z-10 mt-10 space-y-3 md:space-y-2">
          <RevealText
            text="Learning isn't linear."
            as="h2"
            className="mk-display relative z-10 text-[clamp(2.8rem,8vw,6.5rem)]"
          />
          <RevealText
            text="Neither are you."
            as="p"
            delay={0.15}
            className="mk-display relative z-10 text-[clamp(2.8rem,8vw,6.5rem)] text-[var(--mk-accent)] md:pl-[8%]"
          />
        </div>
        <FadeUp delay={0.3}>
          <p className="mk-body relative z-10 mt-12 max-w-xl text-base md:text-lg">
            LOOM is built for non-linear research — the way serious people
            actually move through the web: sideways, recursive, interruptible.
          </p>
        </FadeUp>
      </div>
    </section>
  );
}

export function SiteEngine() {
  return (
    <section className="relative z-20 border-t border-[var(--mk-line)] bg-[var(--mk-bg)] py-24 md:py-32">
      <div className="mk-wrap">
        <FadeUp>
          <p className="mk-label">08 — ENGINE</p>
          <h2 className="mk-display mt-5 max-w-3xl text-[clamp(2rem,4vw,3.4rem)]">
            Technical credibility,
            <br />
            not marketing fog.
          </h2>
        </FadeUp>

        <div className="mt-14 grid gap-px bg-[var(--mk-line)] md:grid-cols-4">
          {[
            ["INPUT", "TEXT / PDF / CONTEXT", "Highlight · copy · dwell · page"],
            ["PROCESS", "RETRIEVE → CONNECT", "Classify · route · dedup"],
            ["MEMORY", "STRUCTURED STORES", "Glossary · claims · deadlines"],
            ["OUTPUT", "UNDERSTANDING", "Ask · evidence · threads"],
          ].map(([k, v, d], i) => (
            <FadeUp key={k} delay={i * 0.06} className="bg-[var(--mk-bg)] p-6 md:p-8">
              <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--mk-accent)]">
                {k}
              </p>
              <p className="mt-4 font-mono text-xs tracking-[0.12em] text-[var(--mk-text)]">
                {v}
              </p>
              <p className="mt-4 text-sm text-[var(--mk-dim)]">{d}</p>
            </FadeUp>
          ))}
        </div>

        <FadeUp delay={0.2}>
          <p className="mt-10 font-mono text-[11px] tracking-[0.14em] text-[var(--mk-faint)]">
            SYSTEM / LOOM CORE · EXTENSION MV3 · FASTAPI · POSTGRES · REDIS
          </p>
        </FadeUp>
      </div>
    </section>
  );
}

export function SiteStats() {
  return (
    <section className="relative z-20 border-t border-[var(--mk-line)] bg-[var(--mk-bg)] py-20">
      <div className="mk-wrap grid gap-10 md:grid-cols-3">
        {[
          { n: 5, suffix: "", label: "PASSIVE SIGNALS" },
          { n: 8, suffix: "", label: "SKILL STORES" },
          { n: 1, suffix: "", label: "MEMORY LAYER" },
        ].map((s, i) => (
          <FadeUp key={s.label} delay={i * 0.08}>
            <p className="mk-display text-6xl md:text-7xl">
              <NumberCounter value={s.n} suffix={s.suffix} />
            </p>
            <p className="mt-3 font-mono text-[11px] tracking-[0.2em] text-[var(--mk-faint)]">
              {s.label}
            </p>
            <div className="mt-6 h-px w-full overflow-hidden bg-[var(--mk-line)]">
              <motion.div
                className="h-full origin-left bg-[var(--mk-accent)]"
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true, amount: 0.4 }}
                transition={{ duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
              />
            </div>
          </FadeUp>
        ))}
      </div>
    </section>
  );
}

export function SiteCta() {
  return (
    <section className="relative z-20 overflow-hidden border-t border-[var(--mk-line)] bg-[var(--mk-bg)]">
      <VantaBackground effect="fog" className="min-h-[70vh]" dim>
        <div className="mk-wrap relative z-10 py-28 text-center md:py-40">
          <FadeUp>
            <p className="mk-label">ENTER</p>
          </FadeUp>
          <RevealText
            text={"Stop studying\naround your brain."}
            as="h2"
            className="mk-display mx-auto mt-8 max-w-4xl text-[clamp(2.6rem,7vw,5.5rem)]"
          />
          <RevealText
            text={"Start building\nwith it."}
            as="p"
            delay={0.2}
            className="mk-display mx-auto mt-4 max-w-4xl text-[clamp(2.6rem,7vw,5.5rem)] text-[var(--mk-accent)]"
          />
          <FadeUp delay={0.35}>
            <div className="mt-12 flex justify-center">
              <MagneticButton href="/sign-up" className="mk-btn mk-btn-primary px-10 py-4 text-[0.75rem]">
                Enter Loom →
              </MagneticButton>
            </div>
          </FadeUp>
        </div>
      </VantaBackground>
    </section>
  );
}

export function SiteFooter() {
  return (
    <footer className="relative z-20 border-t border-[var(--mk-line)] bg-[var(--mk-bg)] py-14">
      <div className="mk-wrap flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="mk-font-display text-sm font-semibold tracking-tight">
            LOOM
          </p>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-[var(--mk-dim)]">
            Learning infrastructure for people who don&apos;t learn linearly.
          </p>
        </div>
        <div className="flex flex-wrap gap-12 text-sm text-[var(--mk-dim)]">
          <div className="space-y-2">
            <p className="mk-label">Product</p>
            <a href="#product" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              Product
            </a>
            <a href="#how" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              How it works
            </a>
            <a href="#research" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              Research
            </a>
          </div>
          <div className="space-y-2">
            <p className="mk-label">App</p>
            <a href="/sign-in" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              Log in
            </a>
            <a href="/sign-up" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              Get started
            </a>
            <a href="/overview" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              Dashboard
            </a>
          </div>
          <div className="space-y-2">
            <p className="mk-label">Legal</p>
            <a href="/legal/privacy" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              Privacy
            </a>
            <a href="/legal/terms" className="block hover:text-[var(--mk-text)]" data-cursor="hover">
              Terms
            </a>
          </div>
        </div>
      </div>
      <div className="mk-wrap mt-12 border-t border-[var(--mk-line)] pt-6">
        <p className="font-mono text-[10px] tracking-[0.16em] text-[var(--mk-faint)]">
          © {new Date().getFullYear()} LOOM ·{" "}
          <a href="/legal/privacy" className="hover:text-[var(--mk-dim)]">
            Privacy
          </a>{" "}
          ·{" "}
          <a href="/legal/terms" className="hover:text-[var(--mk-dim)]">
            Terms
          </a>
        </p>
      </div>
    </footer>
  );
}
