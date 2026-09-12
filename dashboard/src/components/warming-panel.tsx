"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * Honest cold-start state for hosts that sleep the API when idle (e.g. Render).
 */
export function WarmingPanel({
  title = "Waking up the API",
  detail = "The backend was idle and is starting. This can take about a minute.",
  autoRefreshSeconds = 8,
}: {
  title?: string;
  detail?: string;
  autoRefreshSeconds?: number;
}) {
  const router = useRouter();
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const tick = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(tick);
  }, []);

  useEffect(() => {
    if (autoRefreshSeconds <= 0) return;
    const refresh = window.setInterval(() => {
      router.refresh();
    }, autoRefreshSeconds * 1000);
    return () => window.clearInterval(refresh);
  }, [autoRefreshSeconds, router]);

  return (
    <div className="loom-glass loom-sheen-mid p-md">
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <p className="mt-1 text-sm text-text-secondary">{detail}</p>
      <p className="loom-mono mt-sm text-xs text-text-faint">
        Waiting {seconds}s · retrying automatically
      </p>
      <button
        type="button"
        className="loom-btn loom-btn-secondary mt-md"
        onClick={() => router.refresh()}
      >
        Try again now
      </button>
    </div>
  );
}
