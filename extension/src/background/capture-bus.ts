import {
  CAPTURE_EVENT_TYPES,
  type CaptureEvent,
  type CaptureEventType,
  type CaptureFeed,
} from "../capture/types";

/** How many recent events the debug feed keeps. */
const FEED_CAPACITY = 100;

function emptyCounts(): Record<CaptureEventType, number> {
  return Object.fromEntries(CAPTURE_EVENT_TYPES.map((type) => [type, 0])) as Record<
    CaptureEventType,
    number
  >;
}

/**
 * Receives batched capture events from content scripts and the PDF viewer.
 *
 * Phase 2.1 deliberately stores nothing durable — this is an in-memory ring
 * buffer that backs the dev debug feed and proves capture works end to end.
 * Phase 2.2 adds the persisted queue and backend sync.
 */
class CaptureBus {
  private events: CaptureEvent[] = [];
  private counts = emptyCounts();
  private totalReceived = 0;

  ingest(events: CaptureEvent[]): void {
    for (const event of events) {
      this.events.push(event);
      this.totalReceived += 1;
      if (event.type in this.counts) {
        this.counts[event.type] += 1;
      }
    }

    if (this.events.length > FEED_CAPACITY) {
      this.events = this.events.slice(-FEED_CAPACITY);
    }
  }

  getFeed(): CaptureFeed {
    return {
      // Newest first, which is how the debug panel reads.
      events: [...this.events].reverse(),
      counts: { ...this.counts },
      totalReceived: this.totalReceived,
    };
  }

  clear(): void {
    this.events = [];
    this.counts = emptyCounts();
    this.totalReceived = 0;
  }
}

export const captureBus = new CaptureBus();
