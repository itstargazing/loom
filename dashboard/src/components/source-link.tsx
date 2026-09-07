import { hostnameOf } from "@/lib/format";

/** Same source treatment as skill tables — not a raw underline. */
export function SourceLink({
  href,
  children,
}: {
  href: string;
  children?: string | null;
}) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      title={children || href}
      className="text-xs text-text-secondary underline decoration-border underline-offset-2 transition-colors duration-fast hover:text-text-primary"
    >
      {children || hostnameOf(href)}
    </a>
  );
}
