import type { CSSProperties } from "react";

type SignalProps = {
  kind: string;
  body?: string;
  meta?: string;
  style?: CSSProperties;
  className?: string;
  dim?: boolean;
  live?: boolean;
};

/** Editorial fragment — hairline + type, not a SaaS card. */
export function Signal({
  kind,
  body,
  meta,
  style,
  className = "",
  dim = false,
  live = false,
}: SignalProps) {
  return (
    <div
      className={[
        "mk-signal pointer-events-auto select-none",
        dim ? "opacity-30" : "opacity-100",
        className,
      ].join(" ")}
      style={style}
    >
      <div className="flex items-center gap-2">
        {live ? <span className="mk-signal-dot" aria-hidden /> : null}
        <p className="font-mono text-[9px] tracking-[0.24em] text-[var(--mk-faint)]">
          {kind}
        </p>
      </div>
      {body ? (
        <p className="mt-2 max-w-[17rem] font-display text-[15px] leading-[1.35] tracking-tight text-[var(--mk-text)]">
          {body}
        </p>
      ) : null}
      {meta ? (
        <p className="mt-2 font-mono text-[9px] tracking-[0.14em] text-[var(--mk-dim)]">
          {meta}
        </p>
      ) : null}
    </div>
  );
}

export function ChapterLabel({
  index,
  title,
}: {
  index: string;
  title: string;
}) {
  return (
    <p className="font-mono text-[9px] tracking-[0.28em] text-[var(--mk-faint)]">
      <span className="text-[var(--mk-dim)]">{index}</span>
      <span className="mx-3 opacity-40">—</span>
      {title}
    </p>
  );
}
