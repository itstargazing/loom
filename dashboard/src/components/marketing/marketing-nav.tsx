"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import { MagneticButton } from "./motion/primitives";

const LINKS = [
  { href: "#product", label: "Product" },
  { href: "#how", label: "How it works" },
  { href: "#research", label: "Research" },
  { href: "#about", label: "About" },
];

export function MarketingNav() {
  const [compact, setCompact] = useState(false);
  const [active, setActive] = useState("#product");

  useEffect(() => {
    const onScroll = () => {
      setCompact(window.scrollY > 28);
      const ids = LINKS.map((l) => l.href.slice(1));
      let current = ids[0];
      for (const id of ids) {
        const el = document.getElementById(id);
        if (!el) continue;
        if (el.getBoundingClientRect().top <= 120) current = id;
      }
      setActive(`#${current}`);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={[
        "fixed inset-x-0 top-0 z-50 transition-[padding,background-color,border-color,backdrop-filter] duration-300",
        compact
          ? "border-b border-[var(--mk-line)] bg-[rgba(5,5,5,0.82)] py-3 backdrop-blur-md"
          : "border-b border-transparent bg-transparent py-5",
      ].join(" ")}
    >
      <div className="mk-wrap flex items-center justify-between gap-4">
        <Link
          href="/"
          className="flex items-center gap-2.5"
          aria-label="LOOM home"
          data-cursor="hover"
        >
          <Image
            src="/brand/loom-mark-flat.png?v=horn-1"
            alt=""
            width={40}
            height={30}
            className="h-7 w-auto bg-transparent"
            unoptimized
            priority
          />
          <span className="mk-font-display text-sm font-semibold tracking-tight text-[var(--mk-text)]">
            LOOM
          </span>
        </Link>

        <nav
          className="hidden items-center gap-8 md:flex"
          aria-label="Marketing"
        >
          {LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="mk-nav-link"
              data-active={active === link.href}
              data-cursor="hover"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            href="/sign-in"
            className="hidden text-sm text-[var(--mk-dim)] transition-colors hover:text-[var(--mk-text)] sm:inline"
            data-cursor="hover"
          >
            Log in
          </Link>
          <MagneticButton href="/sign-up" className="mk-btn mk-btn-primary">
            Get started
          </MagneticButton>
        </div>
      </div>
    </header>
  );
}
