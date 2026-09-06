/** Hand-drawn capture → route threads. The only load animation on the page. */

export function ThreadIllustration({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 280 180"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path
        className="loom-thread loom-thread-a"
        pathLength={1}
        d="M8 38 C72 8 118 86 198 62 S248 28 272 42"
      />
      <path
        className="loom-thread loom-thread-b"
        pathLength={1}
        d="M8 92 C86 118 138 36 206 98 S246 136 272 124"
      />
      <path
        className="loom-thread loom-thread-c"
        pathLength={1}
        d="M8 154 C64 128 132 168 194 142 S244 96 272 108"
      />
      <circle className="loom-thread-dot" cx="8" cy="38" r="2.4" />
      <circle className="loom-thread-dot" cx="8" cy="92" r="2.4" />
      <circle className="loom-thread-dot" cx="8" cy="154" r="2.4" />
      <circle className="loom-thread-dot" cx="272" cy="42" r="3" />
      <circle className="loom-thread-dot" cx="272" cy="124" r="3" />
      <circle className="loom-thread-dot" cx="272" cy="108" r="3" />
    </svg>
  );
}

export function ThreadSpark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 220 56"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path
        className="loom-spark-a"
        d="M4 40 C28 12 48 48 72 22 C96 -2 118 50 146 28 C174 6 194 38 216 18"
      />
      <path
        className="loom-spark-b"
        d="M4 48 C36 28 58 52 88 36 C118 20 148 54 186 40 C204 34 214 30 216 26"
      />
    </svg>
  );
}
