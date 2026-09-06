import type {
  CaptureBatchMessage,
  CaptureEvent,
  CaptureEventType,
  CapturePayloadFor,
} from "./types";

/** Events are held briefly so a burst of activity becomes one message. */
const FLUSH_INTERVAL_MS = 5000;
/** Flush early once a batch reaches this size. */
const MAX_BATCH_SIZE = 20;
/** Hard cap so a runaway page cannot grow the queue without bound. */
const MAX_QUEUE_SIZE = 200;

/**
 * Batches capture events and forwards them to the background service worker.
 *
 * Nothing is persisted here — Phase 2.2 adds the durable queue and backend sync.
 */
class CaptureEmitter {
  private queue: CaptureEvent[] = [];
  private flushTimer: ReturnType<typeof setTimeout> | null = null;

  emit<T extends CaptureEventType>(type: T, payload: CapturePayloadFor<T>): CaptureEvent {
    const event = {
      id: crypto.randomUUID(),
      type,
      payload,
      sourceUrl: location.href,
      pageTitle: document.title,
      timestamp: new Date().toISOString(),
    } as CaptureEvent;

    if (this.queue.length >= MAX_QUEUE_SIZE) {
      this.queue.shift();
    }
    this.queue.push(event);

    // Highlights and copies flush immediately so classification (and the
    // confirmation toast) is not waiting on the 5s debounce.
    if (
      type === "highlight_selected" ||
      type === "text_copied" ||
      this.queue.length >= MAX_BATCH_SIZE
    ) {
      void this.flush();
      return event;
    }

    this.scheduleFlush();
    return event;
  }

  private scheduleFlush(): void {
    if (this.flushTimer !== null) return;
    this.flushTimer = setTimeout(() => {
      this.flushTimer = null;
      void this.flush();
    }, FLUSH_INTERVAL_MS);
  }

  async flush(): Promise<void> {
    if (this.flushTimer !== null) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
    if (this.queue.length === 0) return;

    const events = this.queue;
    this.queue = [];

    const message: CaptureBatchMessage = { type: "capture:events", events };

    try {
      await chrome.runtime.sendMessage(message);
    } catch {
      // The extension context is invalidated on reload/update. Dropping is
      // acceptable here; Phase 2.2 introduces a persisted queue with retries.
    }
  }

  /** Flush synchronously-ish on page teardown, before listeners are torn down. */
  installLifecycleFlush(): () => void {
    const flushNow = (): void => {
      void this.flush();
    };
    const onVisibilityChange = (): void => {
      if (document.visibilityState === "hidden") flushNow();
    };

    window.addEventListener("pagehide", flushNow);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.removeEventListener("pagehide", flushNow);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }
}

export const captureEmitter = new CaptureEmitter();
export type { CaptureEmitter };
