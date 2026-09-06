/**
 * Browser-side client for the extension bridge.
 *
 * The extension's content script relays these requests to its service worker.
 * If the extension is not installed nothing answers, so every call is bounded
 * by a timeout and reports "not detected" rather than hanging.
 */

import {
  BRIDGE_CHANNEL,
  BRIDGE_READY_ATTRIBUTE,
  isBridgeResponse,
  type BridgeRequest,
  type BridgeRequestType,
  type BridgeSyncOutcome,
  type BridgeSyncStatus,
} from "../../shared/bridge/dashboard-protocol";

export type { BridgeSyncOutcome, BridgeSyncStatus };

/** The content script answers immediately; a sync round trip does not. */
const PING_TIMEOUT_MS = 600;
const REQUEST_TIMEOUT_MS = 30_000;

export class ExtensionUnavailableError extends Error {
  constructor() {
    super("LOOM extension did not respond.");
    this.name = "ExtensionUnavailableError";
  }
}

function request<T>(type: BridgeRequestType, timeoutMs: number): Promise<T> {
  const requestId = crypto.randomUUID();

  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      window.removeEventListener("message", onMessage);
      reject(new ExtensionUnavailableError());
    }, timeoutMs);

    function onMessage(event: MessageEvent) {
      if (event.source !== window) return;
      if (!isBridgeResponse(event.data)) return;
      if (event.data.requestId !== requestId) return;

      window.clearTimeout(timer);
      window.removeEventListener("message", onMessage);

      if (!event.data.ok) {
        reject(new Error(event.data.error ?? "Extension request failed"));
        return;
      }
      resolve(event.data.result as T);
    }

    window.addEventListener("message", onMessage);

    const payload: BridgeRequest = {
      channel: BRIDGE_CHANNEL,
      direction: "request",
      requestId,
      type,
    };
    window.postMessage(payload, window.location.origin);
  });
}

/**
 * True when the extension's bridge is installed on this page.
 *
 * Checks the attribute the bridge sets on `<html>` first, which is set before
 * the page finishes loading, and falls back to a ping in case this code ran
 * before the content script did.
 */
export async function detectExtension(): Promise<boolean> {
  if (document.documentElement.hasAttribute(BRIDGE_READY_ATTRIBUTE)) return true;

  try {
    await request<{ version: string }>("bridge:ping", PING_TIMEOUT_MS);
    return true;
  } catch {
    return false;
  }
}

export function getSyncStatus(): Promise<BridgeSyncStatus> {
  return request<BridgeSyncStatus>("sync:get-status", REQUEST_TIMEOUT_MS);
}

export function triggerSync(): Promise<BridgeSyncOutcome> {
  return request<BridgeSyncOutcome>("sync:now", REQUEST_TIMEOUT_MS);
}
