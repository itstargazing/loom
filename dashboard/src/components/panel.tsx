import type { ReactNode } from "react";

/** Small layout primitives shared by the overview and skill pages. */

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-lg">
      <div>
        <h1 className="loom-display font-display text-xl font-semibold tracking-tight">{title}</h1>
        {description ? (
          <p className="mt-1 text-sm text-text-secondary">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </header>
  );
}

export function Section({
  title,
  aside,
  children,
}: {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-md">
      <div className="flex items-baseline justify-between gap-md">
        <h2 className="font-mono text-xs tracking-wide text-text-secondary">
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

export function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="loom-card flex flex-col gap-xs p-md">
      <span className="font-mono text-xs tracking-wide text-text-secondary">
        {label}
      </span>
      <span className="loom-mono text-xl">{value}</span>
      {hint ? <span className="text-xs text-text-secondary">{hint}</span> : null}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-glass border border-dashed border-border-soft p-xl text-center text-sm text-text-secondary">
      {children}
    </div>
  );
}

/**
 * Shown when the backend could not be reached.
 *
 * Deliberately not an exception: a page with one dead panel is more useful than
 * an error screen, and the message names the thing to fix.
 */
export function ErrorPanel({ title, error }: { title: string; error: string }) {
  return (
    <div className="loom-glass loom-sheen-mid p-md">
      <p className="text-sm font-medium text-error">{title}</p>
      <p className="loom-mono mt-1 text-xs text-error">{error}</p>
    </div>
  );
}
