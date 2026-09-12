/**
 * Optional keep-warm ping for hosts that sleep the API (Render free tier).
 * Does not replace dashboard cold-start retries — only reduces how often they happen.
 *
 * Example (GitHub Actions cron every 10 minutes):
 *   curl -fsS "$LOOM_API_URL/health"
 *
 * Or locally:
 *   LOOM_API_URL=https://your-api.onrender.com node scripts/keep-warm.mjs
 */

const url = (process.env.LOOM_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const target = `${url}/health`;

const response = await fetch(target, { signal: AbortSignal.timeout(60_000) });
if (!response.ok) {
  console.error(`keep-warm failed: ${response.status} ${response.statusText}`);
  process.exit(1);
}
console.log(`keep-warm ok: ${target}`);
