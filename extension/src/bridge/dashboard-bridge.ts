/**
 * Content-script half of the dashboard bridge.
 *
 * Relays a small, fixed set of requests from the LOOM dashboard page to the
 * service worker and posts the reply back. Installed only on the configured
 * dashboard origins, so ordinary browsing pages get no bridge at all.
 */

import {
  BRIDGE_CHANNEL,
  BRIDGE_READY_ATTRIBUTE,
  isBridgeRequest,
  type BridgeRequest,
  type BridgeResponse,
} from "../../../shared/bridge/dashboard-protocol";
import { loadBridgeOrigins } from "./origins";

type ReplyBody = Pick<BridgeResponse, "ok" | "error" | "result">;

function reply(request: BridgeRequest, body: ReplyBody): void {
  const payload: BridgeResponse = {
    channel: BRIDGE_CHANNEL,
    direction: "response",
    requestId: request.requestId,
    ...body,
  };
  // Targeted at this page's own origin; the bridge never broadcasts to "*".
  window.postMessage(payload, window.location.origin);
}

async function handle(request: BridgeRequest): Promise<void> {
  if (request.type === "bridge:ping") {
    reply(request, { ok: true, result: { version: chrome.runtime.getManifest().version } });
    return;
  }

  try {
    const response = await chrome.runtime.sendMessage({ type: request.type });
    if (response?.ok !== true) {
      reply(request, { ok: false, error: response?.error ?? "Extension declined the request" });
      return;
    }
    reply(request, { ok: true, result: response.status ?? response.outcome });
  } catch (error) {
    // Typically "Receiving end does not exist" while the worker restarts.
    const message = error instanceof Error ? error.message : "Extension unreachable";
    reply(request, { ok: false, error: message });
  }
}

export async function initDashboardBridge(): Promise<void> {
  const origins = await loadBridgeOrigins();
  if (!origins.includes(window.location.origin)) return;

  window.addEventListener("message", (event) => {
    // Only same-page messages: a cross-origin frame must not be able to drive
    // the bridge just because the top-level page is the dashboard.
    if (event.source !== window) return;
    if (event.origin !== window.location.origin) return;
    if (!isBridgeRequest(event.data)) return;

    void handle(event.data);
  });

  document.documentElement.setAttribute(
    BRIDGE_READY_ATTRIBUTE,
    chrome.runtime.getManifest().version,
  );
}
