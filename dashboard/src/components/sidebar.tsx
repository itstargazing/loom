"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { EXTRA_SKILL_LINKS, SKILL_VIEWS } from "@/lib/skills";

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname === href;

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={[
        "block whitespace-nowrap rounded-sm px-3 py-1.5 text-sm transition-colors duration-fast",
        active
          ? "bg-glass-2 font-medium text-text-primary"
          : "text-text-secondary hover:bg-glass hover:text-text-primary",
      ].join(" ")}
    >
      {label}
    </Link>
  );
}

const CORE_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/digest", label: "Digest" },
  { href: "/ask", label: "Ask" },
  { href: "/trail", label: "Trail" },
];

const SKILL_LINKS = [
  ...SKILL_VIEWS.map((view) => ({
    href: `/skills/${view.slug}`,
    label: view.label,
  })),
  ...EXTRA_SKILL_LINKS.map((link) => ({
    href: `/skills/${link.slug}`,
    label: link.label,
  })),
];

export function Sidebar() {
  return (
    <>
      <nav
        aria-label="Skills"
        className="loom-glass loom-sheen-tl mx-md mt-md flex flex-col gap-sm p-md md:hidden"
      >
        <div className="flex items-center justify-between gap-md">
          <Link href="/">
            <span className="loom-display font-display text-lg font-semibold tracking-tight">
              LOOM
            </span>
          </Link>
          <span className="font-mono text-[10px] tracking-[0.18em] text-text-faint">
            Capture · Classify · Route
          </span>
        </div>
        <div className="-mx-1 flex gap-xs overflow-x-auto px-1 pb-1">
          {CORE_LINKS.map((link) => (
            <NavLink key={link.href} href={link.href} label={link.label} />
          ))}
          {SKILL_LINKS.map((link) => (
            <NavLink key={link.href} href={link.href} label={link.label} />
          ))}
          <NavLink href="/account" label="Account" />
          <NavLink href="/privacy" label="Local-only" />
          <NavLink href="/style-guide" label="Style guide" />
        </div>
      </nav>

      <nav
        aria-label="Skills"
        className="loom-glass loom-sheen-tl sticky top-lg m-lg hidden h-[calc(100vh-48px)] w-56 shrink-0 flex-col gap-lg p-lg md:flex"
      >
        <Link href="/" className="px-3">
          <span className="loom-display font-display text-lg font-semibold tracking-tight">
            LOOM
          </span>
          <span className="mt-0.5 block font-mono text-[10px] tracking-[0.18em] text-text-faint">
            Capture · Classify · Route
          </span>
        </Link>

        <div className="flex flex-col gap-xs">
          {CORE_LINKS.map((link) => (
            <NavLink key={link.href} href={link.href} label={link.label} />
          ))}
        </div>

        <div className="flex min-h-0 flex-col gap-xs overflow-y-auto">
          <span className="loom-badge mx-3 w-fit">Skills</span>
          {SKILL_LINKS.map((link) => (
            <NavLink key={link.href} href={link.href} label={link.label} />
          ))}
        </div>

        <div className="mt-auto flex flex-col gap-xs">
          <NavLink href="/account" label="Account" />
          <NavLink href="/privacy" label="Local-only" />
          <NavLink href="/style-guide" label="Style guide" />
        </div>
      </nav>
    </>
  );
}
