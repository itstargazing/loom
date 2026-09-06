import type { CaptureEvent } from "../capture/types";
import { loadSyncConfig } from "./sync-config";
import {
  enqueue,
  peekBatch,
  queueLength,
  readSyncState,
  removeEvents,
  updateSyncState,
  type SyncState,
} from "./sync-queue";

const SYNC_ALARM = "loom:sync";
/** chrome.alarms enforces a one-minute minimum period. */
const SYNC_PERIOD_MINUTES = 1;
const IDLE_DETECTION_SECONDS = 60;

/** Must stay at or below the backend's max_events_per_batch. */
const BATCH_SIZE = 50;
/** Batches drained per invocation, so a large backlog clears without stalling. */
const MAX_BATCHES_PER_RUN = 5;

const BASE_BACKOFF_MS = 5_000;
const MAX_BACKOFF_MS = 5 * 60_000;

export type SyncOutcome =
  | { status: "synced"; sent: number; remaining: number }
  | { status: "empty" }
  | { status: "busy" }
  | { status: "backoff"; retryInMs: number }
  | { status: "failed"; error: string; retryInMs: number };

/** Exponential backoff with jitter, so many clients do not retry in lockstep. */
function backoffFor(failureCount: number): number {
  const exponential = Math.min(
    BASE_BACKOFF_MS * 2 ** Math.max(0, failureCount - 1),
    MAX_BACKOFF_MS,
  );
  const jitter = exponential * 0.2 * (Math.random() * 2 - 1);
  return Math.round(exponential + jitter);
}

let running = false;

interface SendResult {
  ok: boolean;
  /** True when the backend rejected the batch on its merits, not transiently. */
  permanent: boolean;
  error?: string;
}

async function sendBatch(events: CaptureEvent[]): Promise<SendResult> {
  const config = await loadSyncConfig();

  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}/api/capture/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.authToken}`,
      },
      body: JSON.stringify({ events }),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network request failed";
    return { ok: false, permanent: false, error: message };
  }

  if (response.ok) return { ok: true, permanent: false };

  // 4xx means this payload will never be accepted, so retrying it forever would
  // block every event behind it. 408 and 429 are the transient exceptions.
  const permanent =
    response.status >= 400 &&
    response.status < 500 &&
    response.status !== 408 &&
    response.status !== 429;

  return {
    ok: false,
    permanent,
    error: `HTTP ${response.status} ${response.statusText}`.trim(),
  };
}

function onSuccess(sent: number) {
  return (state: SyncState): SyncState => ({
    ...state,
    failureCount: 0,
    nextAttemptAtMs: 0,
    lastError: null,
    lastSyncedAtMs: Date.now(),
    totalSynced: state.totalSynced + sent,
  });
}

function onFailure(error: string, retryInMs: number) {
  return (state: SyncState): SyncState => ({
    ...state,
    failureCount: state.failureCount + 1,
    nextAttemptAtMs: Date.now() + retryInMs,
    lastError: error,
  });
}

/**
 * Drain the queue to the backend.
 *
 * `force` skips the backoff window and is only used by the manual sync button.
 */
export async function syncNow(reason: string, force = false): Promise<SyncOutcome> {
  if (running) return { status: "busy" };

  const state = await readSyncState();
  const waitMs = state.nextAttemptAtMs - Date.now();
  if (!force && waitMs > 0) {
    return { status: "backoff", retryInMs: waitMs };
  }

  running = true;
  let sent = 0;

  try {
    for (let batchIndex = 0; batchIndex < MAX_BATCHES_PER_RUN; batchIndex += 1) {
      const batch = await peekBatch(BATCH_SIZE);
      if (batch.length === 0) break;

      const result = await sendBatch(batch);

      if (result.ok) {
        await removeEvents(new Set(batch.map((event) => event.id)));
        sent += batch.length;
        await updateSyncState(onSuccess(batch.length));
        continue;
      }

      if (result.permanent) {
        // Drop the rejected batch rather than letting it wedge the queue.
        await removeEvents(new Set(batch.map((event) => event.id)));
        console.error(
          `[LOOM] Dropped ${batch.length} event(s) rejected by the backend: ${result.error}`,
        );
        await updateSyncState((current) => ({
          ...current,
          lastError: `Rejected: ${result.error}`,
        }));
        continue;
      }

      const retryInMs = backoffFor(state.failureCount + 1);
      await updateSyncState(onFailure(result.error ?? "Unknown error", retryInMs));
      console.warn(
        `[LOOM] Sync (${reason}) failed: ${result.error}. Retrying in ${Math.round(retryInMs / 1000)}s.`,
      );
      return { status: "failed", error: result.error ?? "Unknown error", retryInMs };
    }
  } finally {
    running = false;
  }

  const remaining = await queueLength();
  if (sent === 0) return { status: "empty" };

  console.info(`[LOOM] Sync (${reason}) sent ${sent} event(s), ${remaining} queued.`);
  return { status: "synced", sent, remaining };
}

/** Queue newly captured events and try to send them promptly. */
export async function queueForSync(events: CaptureEvent[]): Promise<void> {
  if (events.length === 0) return;
  await enqueue(events);
  await syncNow("capture");
}

export interface SyncStatus extends SyncState {
  queued: number;
  apiBaseUrl: string;
}

export async function getSyncStatus(): Promise<SyncStatus> {
  const [state, queued, config] = await Promise.all([
    readSyncState(),
    queueLength(),
    loadSyncConfig(),
  ]);
  return { ...state, queued, apiBaseUrl: config.apiBaseUrl };
}

/**
 * Register the periodic and idle sync triggers.
 *
 * chrome.alarms is used instead of setInterval because the service worker is
 * terminated when idle, which would cancel any timer.
 */
export function initSync(): void {
  chrome.alarms.create(SYNC_ALARM, { periodInMinutes: SYNC_PERIOD_MINUTES });

  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === SYNC_ALARM) void syncNow("alarm");
  });

  chrome.idle.setDetectionInterval(IDLE_DETECTION_SECONDS);
  chrome.idle.onStateChanged.addListener((newState) => {
    // Browsing has paused, so a sync now costs the user nothing.
    if (newState !== "active") void syncNow("idle");
  });

  console.info("[LOOM] Sync scheduler initialized.");
}
