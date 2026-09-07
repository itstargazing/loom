/**
 * Server-side client for the LOOM backend.
 *
 * Every call returns a result object instead of throwing. A dashboard that
 * renders a "backend unreachable" panel is far more useful during local
 * development than one that returns a 500, and the pages need to distinguish
 * "no data yet" from "could not ask" anyway.
 */

import type { DashboardOverview } from "./types";

export const API_BASE_URL = process.env.LOOM_API_URL ?? "http://localhost:8000";

const AUTH_TOKEN = process.env.LOOM_API_TOKEN ?? "loom-dev-token";

/** Long enough for a cold backend, short enough not to hang a page render. */
const TIMEOUT_MS = 8_000;

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

function describe(error: unknown): string {
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return `No response from ${API_BASE_URL} within ${TIMEOUT_MS / 1000}s.`;
  }
  if (error instanceof Error) {
    // Node's fetch reports a bare "fetch failed" for a refused connection,
    // which tells the reader nothing about what to fix.
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

export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number>,
): Promise<ApiResult<T>> {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    url.searchParams.set(key, String(value));
  }

  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      signal: AbortSignal.timeout(TIMEOUT_MS),
      // The pipeline writes continuously, so a cached page would be misleading.
      cache: "no-store",
    });
  } catch (error) {
    return { ok: false, error: describe(error) };
  }

  if (!response.ok) {
    const hint =
      response.status === 401 || response.status === 403
        ? " Check LOOM_API_TOKEN."
        : "";
    return {
      ok: false,
      error: `Backend returned ${response.status} ${response.statusText}.${hint}`,
    };
  }

  try {
    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    return { ok: false, error: `Malformed response body: ${describe(error)}` };
  }
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
