/**
 * Server-side client for the LOOM backend.
 *
 * Every call returns a result object instead of throwing. A dashboard that
 * renders a "backend unreachable" panel is far more useful during local
 * development than one that returns a 500, and the pages need to distinguish
 * "no data yet" from "could not ask" anyway.
 */

import type { DashboardOverview } from "./types";
import { resolveApiBearerToken } from "./api-token";

export const API_BASE_URL = process.env.LOOM_API_URL ?? "http://localhost:8000";

/** Per-attempt timeout. Cold Render instances often need more than one try. */
const ATTEMPT_TIMEOUT_MS = 25_000;
/** Total wall time across retries — enough for a spin-up after idle. */
const MAX_WAIT_MS = 90_000;
const MAX_ATTEMPTS = 4;

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; warming?: boolean };

function describe(error: unknown, attemptTimeoutMs: number): string {
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return `No response from ${API_BASE_URL} within ${Math.round(attemptTimeoutMs / 1000)}s.`;
  }
  if (error instanceof Error) {
    if (error.message === "fetch failed") {
      const onVercel =
        process.env.VERCEL === "1" &&
        (API_BASE_URL.includes("localhost") || API_BASE_URL.includes("127.0.0.1"));
      if (onVercel) {
        return "This Vercel deploy has no public API. Set LOOM_API_URL to a hosted FastAPI URL (not localhost) and redeploy.";
      }
      return `Cannot reach the backend at ${API_BASE_URL}. Is it running?`;
    }
    return error.message;
  }
  return "Unknown error";
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryable(error: unknown, status?: number): boolean {
  if (status !== undefined) {
    return status === 502 || status === 503 || status === 504;
  }
  if (error instanceof DOMException && error.name === "TimeoutError") return true;
  if (error instanceof Error && error.message === "fetch failed") return true;
  return false;
}

async function apiGetOnce<T>(
  path: string,
  params: Record<string, string | number> | undefined,
  token: string,
  timeoutMs: number,
): Promise<ApiResult<T> & { retryable?: boolean }> {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    url.searchParams.set(key, String(value));
  }

  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(timeoutMs),
      cache: "no-store",
    });
  } catch (error) {
    return {
      ok: false,
      error: describe(error, timeoutMs),
      retryable: isRetryable(error),
      warming: isRetryable(error),
    };
  }

  if (!response.ok) {
    const hint =
      response.status === 401 || response.status === 403
        ? " Check that you are signed in and the backend AUTH_MODE=jwt accepts Clerk tokens."
        : "";
    return {
      ok: false,
      error: `Backend returned ${response.status} ${response.statusText}.${hint}`,
      retryable: isRetryable(undefined, response.status),
      warming: isRetryable(undefined, response.status),
    };
  }

  try {
    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    return { ok: false, error: `Malformed response body: ${describe(error, timeoutMs)}` };
  }
}

export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number>,
): Promise<ApiResult<T>> {
  let token: string;
  try {
    token = await resolveApiBearerToken();
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : "Could not resolve API token",
    };
  }

  const started = Date.now();
  let last: ApiResult<T> & { retryable?: boolean } = {
    ok: false,
    error: "No attempt made",
  };

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const remaining = MAX_WAIT_MS - (Date.now() - started);
    if (remaining <= 0) break;

    const timeoutMs = Math.min(ATTEMPT_TIMEOUT_MS, remaining);
    last = await apiGetOnce<T>(path, params, token, timeoutMs);
    if (last.ok) return last;
    if (!last.retryable || attempt === MAX_ATTEMPTS) {
      return {
        ok: false,
        error: last.error,
        warming: last.warming,
      };
    }

    const backoff = Math.min(2_000 * 2 ** (attempt - 1), 8_000);
    if (Date.now() - started + backoff >= MAX_WAIT_MS) break;
    await sleep(backoff);
  }

  return {
    ok: false,
    error: last.error,
    warming: true,
  };
}

export function getOverview(activityLimit = 20): Promise<ApiResult<DashboardOverview>> {
  return apiGet<DashboardOverview>("/api/overview", {
    activity_limit: activityLimit,
  });
}

export function getSkillEntries<T>(
  slug: string,
  {
    limit = 50,
    offset = 0,
    q,
    sort,
    collectionId,
  }: {
    limit?: number;
    offset?: number;
    q?: string;
    sort?: "recent" | "alpha";
    collectionId?: string;
  } = {},
): Promise<ApiResult<T[]>> {
  const params: Record<string, string | number> = { limit, offset };
  if (q) params.q = q;
  if (sort) params.sort = sort;
  if (collectionId) params.collection_id = collectionId;
  return apiGet<T[]>(`/api/skills/${slug}`, params);
}

export function getCollections(): Promise<ApiResult<import("./types").Collection[]>> {
  return apiGet("/api/collections");
}

export function getFormProfiles(): Promise<
  ApiResult<import("./types").FormProfile[]>
> {
  return apiGet("/api/skills/form-filler/profiles");
}

export function getFormDocuments(): Promise<
  ApiResult<import("./types").FormDocument[]>
> {
  return apiGet("/api/skills/form-filler/documents");
}

export function getWatchedSets(): Promise<
  ApiResult<import("./types").WatchedSet[]>
> {
  return apiGet("/api/skills/live-doc-diff/sets");
}

export function getRecentDocuments(): Promise<
  ApiResult<import("./types").RecentDocument[]>
> {
  return apiGet("/api/skills/auto-attach/documents");
}

export function getPrivacySettings(): Promise<
  ApiResult<import("./types").PrivacySettings>
> {
  return apiGet("/api/privacy/settings");
}

export function getAccount(): Promise<ApiResult<import("./types").Account>> {
  return apiGet("/api/auth/me");
}

export function getDigest(): Promise<ApiResult<import("./types").Digest>> {
  return apiGet("/api/digest");
}

export function getTrail(limit = 80): Promise<ApiResult<import("./types").Trail>> {
  return apiGet("/api/trail", { limit });
}

export function getNotifications(): Promise<ApiResult<import("./types").NotificationList>> {
  return apiGet("/api/notifications");
}

export function getBriefs(): Promise<ApiResult<import("./types").Brief[]>> {
  return apiGet("/api/briefs");
}
