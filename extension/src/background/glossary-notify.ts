/**
 * After a highlight or copy is synced, poll until it is classified. If it
 * landed in the glossary or citations store, tell the originating tab so it
 * can show a confirmation toast.
 *
 * Classification is asynchronous (Redis → worker → model), so this waits rather
 * than assuming the POST return means the entry is already filed.
 */

import type { CaptureEvent } from "../capture/types";
import { loadSyncConfig } from "./sync-config";

const POLL_MS = 400;
const GIVE_UP_MS = 20_000;

interface ClassificationRow {
  status: string;
  categories: string[];
  result: {
    classifications: Array<{
      category: string;
      fields: { term: string | null; quote: string | null };
    }>;
  } | null;
}

async function fetchClassification(
  apiBaseUrl: string,
  authToken: string,
  eventId: string,
): Promise<ClassificationRow | null> {
  const url = new URL("/api/classifications", apiBaseUrl);
  url.searchParams.set("capture_event_id", eventId);
  url.searchParams.set("limit", "1");

  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  if (!response.ok) return null;

  const rows = (await response.json()) as ClassificationRow[];
  return rows[0] ?? null;
}

function fieldOf(
  row: ClassificationRow,
  category: string,
  field: "term" | "quote",
): string | null {
  if (row.status !== "succeeded") return null;
  if (!row.categories.includes(category)) return null;
  const item = row.result?.classifications.find((entry) => entry.category === category);
  return item?.fields[field] ?? null;
}

async function waitForField(
  apiBaseUrl: string,
  authToken: string,
  eventId: string,
  category: string,
  field: "term" | "quote",
): Promise<string | null> {
  const deadline = Date.now() + GIVE_UP_MS;

  while (Date.now() < deadline) {
    try {
      const row = await fetchClassification(apiBaseUrl, authToken, eventId);
      if (row) {
        return fieldOf(row, category, field);
      }
    } catch {
      // Network blip; keep polling until the deadline.
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  }

  return null;
}

async function notifyTab(
  tabId: number,
  message: Record<string, string>,
): Promise<void> {
  try {
    await chrome.tabs.sendMessage(tabId, message);
  } catch {
    // Tab navigated away or has no content script; the entry is still stored.
  }
}

export async function notifyClassifiedSkills(
  events: CaptureEvent[],
  tabId: number | undefined,
): Promise<void> {
  if (tabId === undefined) return;

  const highlights = events.filter((event) => event.type === "highlight_selected");
  const copies = events.filter((event) => event.type === "text_copied");
  if (highlights.length === 0 && copies.length === 0) return;

  const config = await loadSyncConfig();

  for (const event of highlights) {
    const term = await waitForField(
      config.apiBaseUrl,
      config.authToken,
      event.id,
      "glossary_term",
      "term",
    );
    if (term) {
      await notifyTab(tabId, {
        type: "glossary:captured",
        eventId: event.id,
        term,
      });
    }
  }

  for (const event of copies) {
    const quote = await waitForField(
      config.apiBaseUrl,
      config.authToken,
      event.id,
      "citation",
      "quote",
    );
    if (quote) {
      await notifyTab(tabId, {
        type: "citation:captured",
        eventId: event.id,
        quote,
      });
    }
  }
}

/** @deprecated Use notifyClassifiedSkills. Kept for the glossary-only call sites. */
export const notifyGlossaryHighlights = notifyClassifiedSkills;
