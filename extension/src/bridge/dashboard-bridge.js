/**
 * Content-script half of the dashboard bridge.
 *
 * Relays a small, fixed set of requests from the LOOM dashboard page to the
 * service worker and posts the reply back. Installed only on the configured
 * dashboard origins, so ordinary browsing pages get no bridge at all.
 */
import { BRIDGE_CHANNEL, BRIDGE_READY_ATTRIBUTE, isBridgeRequest, } from "../../../shared/bridge/dashboard-protocol";
import { isBridgeOriginAllowed } from "./origins";
function reply(request, body) {
    const payload = {
        channel: BRIDGE_CHANNEL,
        direction: "response",
        requestId: request.requestId,
        ...body,
    };
    window.postMessage(payload, window.location.origin);
}
async function handle(request) {
    if (request.type === "bridge:ping") {
        reply(request, { ok: true, result: { version: chrome.runtime.getManifest().version } });
        return;
    }
    try {
        const message = { type: request.type };
        if (request.type === "sync:now" && request.payload?.authToken) {
            message.authToken = request.payload.authToken;
        }
        const response = await chrome.runtime.sendMessage(message);
        if (response?.ok !== true) {
            reply(request, { ok: false, error: response?.error ?? "Extension declined the request" });
            return;
        }
        reply(request, { ok: true, result: response.status ?? response.outcome });
    }
    catch (error) {
        const message = error instanceof Error ? error.message : "Extension unreachable";
        reply(request, { ok: false, error: message });
    }
}
export async function initDashboardBridge() {
    const origin = window.location.origin;
    if (!(await isBridgeOriginAllowed(origin))) {
        console.info("[LOOM] Dashboard bridge skipped — origin not allowlisted:", origin, "(add it under extension Options → Dashboard origins)");
        return;
    }
    window.addEventListener("message", (event) => {
        if (event.source !== window)
            return;
        if (event.origin !== window.location.origin)
            return;
        if (!isBridgeRequest(event.data))
            return;
        void handle(event.data);
    });
    document.documentElement.setAttribute(BRIDGE_READY_ATTRIBUTE, chrome.runtime.getManifest().version);
}
