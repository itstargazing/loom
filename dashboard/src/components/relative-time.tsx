"use client";

import { useEffect, useState } from "react";

import { formatRelative, formatUtc } from "@/lib/format";

/**
 * Renders a timestamp as "3 minutes ago", refreshing while the page is open.
 *
 * The first paint is the fixed UTC string so the server and client agree; the
 * relative label is swapped in after mount.
 */
export function RelativeTime({ iso }: { iso: string }) {
  const absolute = formatUtc(iso);
  const [label, setLabel] = useState(absolute);

  useEffect(() => {
    const update = () => setLabel(formatRelative(iso));
    update();
    const timer = window.setInterval(update, 30_000);
    return () => window.clearInterval(timer);
  }, [iso]);

  return (
    <time dateTime={iso} title={absolute} suppressHydrationWarning>
      {label}
    </time>
  );
}
