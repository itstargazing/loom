/**
 * LOOM content script — injected on all pages.
 * Installs the passive capture signals the user has enabled, and on the
 * dashboard origin, the bridge that lets the dashboard trigger a sync.
 */

import { initDashboardBridge } from "../bridge/dashboard-bridge";
import { initCapture } from "../capture";
import { showCitationConfirmation } from "../capture/citation-overlay";
import { showGlossaryConfirmation } from "../capture/glossary-overlay";

const pendingHighlights = new Map<string, DOMRect | null>();
const pendingCopies = new Map<string, DOMRect | null>();

void initCapture({
  onHighlight: (eventId, rect) => {
    pendingHighlights.set(eventId, rect);
  },
  onCopy: (eventId, rect) => {
    pendingCopies.set(eventId, rect);
  },
}).catch((error) => {
  console.warn("[LOOM] Capture failed to initialize:", error);
});

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === "glossary:captured") {
    const rect = pendingHighlights.get(message.eventId) ?? null;
    pendingHighlights.delete(message.eventId);
    showGlossaryConfirmation(String(message.term ?? ""), rect);
    return;
  }

  if (message?.type === "citation:captured") {
    const rect = pendingCopies.get(message.eventId) ?? null;
    pendingCopies.delete(message.eventId);
    showCitationConfirmation(String(message.quote ?? ""), rect);
  }
});

void initDashboardBridge().catch((error) => {
  console.warn("[LOOM] Dashboard bridge failed to initialize:", error);
});
