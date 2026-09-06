import Link from "next/link";

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-border-soft py-12 last:border-b-0">
      <h2 className="loom-display font-display text-xl font-semibold tracking-tight">{title}</h2>
      {description && (
        <p className="mt-2 max-w-2xl text-sm text-text-secondary">{description}</p>
      )}
      <div className="mt-8">{children}</div>
    </section>
  );
}

function Swatch({ name, hex, className }: { name: string; hex: string; className: string }) {
  return (
    <div className="flex flex-col gap-2">
      <div className={`h-16 w-full rounded-sm border border-border ${className}`} />
      <div>
        <p className="font-display text-sm font-medium">{name}</p>
        <p className="font-mono text-xs text-text-secondary">{hex}</p>
      </div>
    </div>
  );
}

export default function StyleGuidePage() {
  return (
    <div className="mx-auto max-w-[920px]">
      <header className="mb-8">
        <Link
          href="/"
          className="font-mono text-xs text-text-secondary transition-colors duration-fast hover:text-text-primary"
        >
          ← Back to dashboard
        </Link>
        <h1 className="loom-display font-display mt-4 text-2xl font-semibold tracking-tight">
          LOOM Style Guide
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-text-secondary">
          Shared liquid-glass tokens for the dashboard and extension. Monochrome
          only — no hue in accents, status, or motion.
        </p>
      </header>

      <Section title="Colors" description="Depth, glass, type, and greyscale status.">
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4">
          <Swatch name="bg-0" hex="#050505" className="bg-bg-0" />
          <Swatch name="bg-1" hex="#0d0d0d" className="bg-bg-1" />
          <Swatch name="Glass" hex="rgba(255,255,255,0.055)" className="bg-glass" />
          <Swatch name="Glass 2" hex="rgba(255,255,255,0.09)" className="bg-glass-2" />
          <Swatch name="Text" hex="#F2F0EC" className="bg-text-primary" />
          <Swatch name="Text dim" hex="#9A988F" className="bg-text-secondary" />
          <Swatch name="Text faint" hex="#5C5A54" className="bg-text-faint" />
          <Swatch name="Border" hex="rgba(255,255,255,0.14)" className="bg-border" />
        </div>
      </Section>

      <Section
        title="Typography"
        description="Space Grotesk for headlines and the pipeline numeral. JetBrains Mono for labels, data, and pills. System sans for long-form body."
      >
        <div className="space-y-8">
          <div>
            <span className="loom-badge mb-4">Space Grotesk</span>
            <p className="font-display text-2xl font-semibold">Heading — 24px semibold</p>
            <p className="font-display mt-2 text-lg font-medium">Subheading — 16px medium</p>
            <p className="font-display mt-2 text-stage font-bold leading-none">01</p>
          </div>
          <hr className="loom-divider" />
          <div>
            <span className="loom-badge mb-4">JetBrains Mono</span>
            <p className="font-mono text-sm">capture_event_id: 8f3a2b1c-4d5e-6f7a</p>
            <p className="mt-2 font-mono text-sm text-text-secondary">
              glossary · citation · deadline
            </p>
          </div>
        </div>
      </Section>

      <Section title="Buttons" description="Pill-shaped. Focus ring is 2px solid text, not the glass border.">
        <div className="flex flex-wrap items-center gap-4">
          <button type="button" className="loom-btn">
            Primary action
          </button>
          <button type="button" className="loom-btn loom-btn-secondary">
            Secondary action
          </button>
          <button type="button" className="loom-icon-btn" aria-label="Icon button">
            +
          </button>
          <button type="button" className="loom-btn" disabled>
            Disabled
          </button>
        </div>
      </Section>

      <Section title="Form elements">
        <div className="max-w-sm space-y-4">
          <div>
            <label htmlFor="demo-input" className="mb-2 block font-mono text-xs text-text-secondary">
              Text input
            </label>
            <input
              id="demo-input"
              type="text"
              className="loom-input"
              placeholder="Enter a value…"
            />
          </div>
          <div className="flex items-center gap-md">
            <button
              type="button"
              className="loom-switch"
              role="switch"
              aria-checked="true"
              aria-label="Demo switch on"
            />
            <button
              type="button"
              className="loom-switch"
              role="switch"
              aria-checked="false"
              aria-label="Demo switch off"
            />
          </div>
        </div>
      </Section>

      <Section title="Pills">
        <div className="flex flex-wrap gap-3">
          <span className="loom-badge">Welcome back</span>
          <span className="loom-badge loom-badge-success">Captured</span>
          <span className="loom-badge loom-badge-warning">Low confidence</span>
          <span className="loom-badge loom-badge-error">Sync failed</span>
        </div>
      </Section>

      <Section title="Glass panels" description="Hero, pipeline, and Route next use the brighter diagonal wash. Nested panels drop backdrop-filter so blur does not stack.">
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="loom-glass loom-glass-bright loom-sheen-tl p-lg">
            <h3 className="font-display text-sm font-semibold">Bright glass</h3>
            <p className="mt-2 text-sm text-text-secondary">
              Diagonal wash for important panels.
            </p>
          </div>
          <div className="loom-glass loom-sheen-tr p-lg">
            <h3 className="font-display text-sm font-semibold">Base glass</h3>
            <hr className="loom-divider my-4" />
            <p className="text-sm text-text-secondary">
              Soft sheen, 28px radius, inset highlight.
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}
