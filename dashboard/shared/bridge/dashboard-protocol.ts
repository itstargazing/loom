/**
 * Message contract between the LOOM dashboard page and the extension.
 *
 * The dashboard reaches the service worker through the content script rather
 * than `chrome.runtime.sendMessage(extensionId, ...)`, because the unpacked
 * extension's ID changes between installs and the dashboard would otherwise
 * need it configured. The content script already runs on every page, so a
 * `window.postMessage` relay works with no extra configuration.
 *
 * Only the request types listed here are relayed, so a page cannot use the
 * bridge to drive arbitrary extension messages.
 */

export const BRIDGE_CHANNEL = "loom-dashboard-bridge";

/** Set on `<html>` by the bridge so the page can detect the extension. */
export const BRIDGE_READY_ATTRIBUTE = "data-loom-bridge";

export const BRIDGE_REQUEST_TYPES = ["bridge:ping", "sync:get-status", "sync:now"] as const;

export type BridgeRequestType = (typeof BRIDGE_REQUEST_TYPES)[number];

export interface BridgeRequest {
  channel: typeof BRIDGE_CHANNEL;
  direction: "request";
  requestId: string;
  type: BridgeRequestType;
}

export interface BridgeResponse {
  channel: typeof BRIDGE_CHANNEL;
  direction: "response";
  requestId: string;
  ok: boolean;
  error?: string;
  /** The service worker's reply, shaped by the request type. */
  result?: unknown;
}

/** Mirrors the extension's `SyncStatus`. */
export interface BridgeSyncStatus {
  queued: number;
  apiBaseUrl: string;
  failureCount: number;
  nextAttemptAtMs: number;
  lastSyncedAtMs: number | null;
  lastError: string | null;
  totalSynced: number;
  totalDropped: number;
}

export type BridgeSyncOutcome =
  | { status: "synced"; sent: number; remaining: number }
  | { status: "empty" }
  | { status: "busy" }
  | { status: "backoff"; retryInMs: number }
  | { status: "failed"; error: string; retryInMs: number };

export function isBridgeRequest(value: unknown): value is BridgeRequest {
  const message = value as Partial<BridgeRequest> | null;
  return (
    !!message &&
    message.channel === BRIDGE_CHANNEL &&
    message.direction === "request" &&
    typeof message.requestId === "string" &&
    BRIDGE_REQUEST_TYPES.includes(message.type as BridgeRequestType)
  );
}

export function isBridgeResponse(value: unknown): value is BridgeResponse {
  const message = value as Partial<BridgeResponse> | null;
  return (
    !!message &&
    message.channel === BRIDGE_CHANNEL &&
    message.direction === "response" &&
    typeof message.requestId === "string" &&
    typeof message.ok === "boolean"
  );
}
