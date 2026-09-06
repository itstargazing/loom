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
export const BRIDGE_REQUEST_TYPES = ["bridge:ping", "sync:get-status", "sync:now"];
export function isBridgeRequest(value) {
    const message = value;
    return (!!message &&
        message.channel === BRIDGE_CHANNEL &&
        message.direction === "request" &&
        typeof message.requestId === "string" &&
        BRIDGE_REQUEST_TYPES.includes(message.type));
}
export function isBridgeResponse(value) {
    const message = value;
    return (!!message &&
        message.channel === BRIDGE_CHANNEL &&
        message.direction === "response" &&
        typeof message.requestId === "string" &&
        typeof message.ok === "boolean");
}
