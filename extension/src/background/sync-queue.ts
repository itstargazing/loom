import type { CaptureEvent } from "../capture/types";

/**
 * Durable outbound queue for capture events.
 *
 * Backed by chrome.storage.local rather than memory because an MV3 service
 * worker is terminated whenever it goes idle — anything held only in memory
 * would be lost between a capture and the next sync.
 */

const QUEUE_KEY = "loom:sync-queue";
const STATE_KEY = "loom:sync-state";

/** Oldest events are dropped past this point, e.g. after a long outage. */
const MAX_QUEUE_LENGTH = 2000;

export interface SyncState {
  /** Consecutive failed attempts, drives the backoff delay. */
  failureCount: number;
  /** Epoch ms before which no attempt should be made. */
  nextAttemptAtMs: number;
  lastSyncedAtMs: number | null;
  lastError: string | null;
  totalSynced: number;
  totalDropped: number;
}

const INITIAL_STATE: SyncState = {
  failureCount: 0,
  nextAttemptAtMs: 0,
  lastSyncedAtMs: null,
  lastError: null,
  totalSynced: 0,
  totalDropped: 0,
};

/**
 * Serializes storage read-modify-write cycles.
 *
 * Sync can be triggered by a message, an alarm, and an idle transition at
 * roughly the same time; without this, interleaved reads would clobber each
 * other's writes.
 */
let tail: Promise<unknown> = Promise.resolve();

function withLock<T>(operation: () => Promise<T>): Promise<T> {
  const result = tail.then(operation, operation);
  tail = result.catch(() => undefined);
  return result;
}

async function readQueue(): Promise<CaptureEvent[]> {
  const stored = await chrome.storage.local.get(QUEUE_KEY);
  return (stored[QUEUE_KEY] ?? []) as CaptureEvent[];
}

async function writeQueue(events: CaptureEvent[]): Promise<void> {
  await chrome.storage.local.set({ [QUEUE_KEY]: events });
}

export async function readSyncState(): Promise<SyncState> {
  const stored = await chrome.storage.local.get(STATE_KEY);
  return { ...INITIAL_STATE, ...((stored[STATE_KEY] ?? {}) as Partial<SyncState>) };
}

async function writeSyncState(state: SyncState): Promise<void> {
  await chrome.storage.local.set({ [STATE_KEY]: state });
}

export function updateSyncState(
  change: (state: SyncState) => SyncState,
): Promise<SyncState> {
  return withLock(async () => {
    const next = change(await readSyncState());
    await writeSyncState(next);
    return next;
  });
}

/** Append events to the queue. Returns the resulting queue length. */
export function enqueue(events: CaptureEvent[]): Promise<number> {
  return withLock(async () => {
    if (events.length === 0) return (await readQueue()).length;

    const queue = [...(await readQueue()), ...events];
    const overflow = queue.length - MAX_QUEUE_LENGTH;

    if (overflow > 0) {
      queue.splice(0, overflow);
      await updateSyncStateUnlocked((state) => ({
        ...state,
        totalDropped: state.totalDropped + overflow,
      }));
    }

    await writeQueue(queue);
    return queue.length;
  });
}

/** State update used from inside an existing lock, to avoid deadlocking. */
async function updateSyncStateUnlocked(
  change: (state: SyncState) => SyncState,
): Promise<void> {
  await writeSyncState(change(await readSyncState()));
}

/** Read the next batch without removing it, so a failed send can be retried. */
export function peekBatch(size: number): Promise<CaptureEvent[]> {
  return withLock(async () => (await readQueue()).slice(0, size));
}

/** Remove events that were accepted by the backend. */
export function removeEvents(sentIds: Set<string>): Promise<number> {
  return withLock(async () => {
    const remaining = (await readQueue()).filter((event) => !sentIds.has(event.id));
    await writeQueue(remaining);
    return remaining.length;
  });
}

export function queueLength(): Promise<number> {
  return withLock(async () => (await readQueue()).length);
}
