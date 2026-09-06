/** Presentation helpers shared by the overview and skill pages. */

const UNITS: Array<[Intl.RelativeTimeFormatUnit, number]> = [
  ["year", 365 * 24 * 60 * 60 * 1000],
  ["month", 30 * 24 * 60 * 60 * 1000],
  ["day", 24 * 60 * 60 * 1000],
  ["hour", 60 * 60 * 1000],
  ["minute", 60 * 1000],
];

const relative = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/**
 * Fixed UTC rendering.
 *
 * Used for the server-rendered pass and for tooltips, because anything
 * locale- or clock-dependent would differ between server and client and trip
 * React's hydration check.
 */
export function formatUtc(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "unknown";
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export function formatRelative(iso: string, now = Date.now()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "unknown";

  const elapsed = date.getTime() - now;
  for (const [unit, ms] of UNITS) {
    if (Math.abs(elapsed) >= ms) {
      return relative.format(Math.round(elapsed / ms), unit);
    }
  }
  return "just now";
}

export function formatCount(value: number): string {
  return value.toLocaleString("en-US");
}

/** Confidence reads better as a whole percentage than as 0.82. */
export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
