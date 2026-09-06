import { buildViewerUrl, isPdfUrl } from "./types";
/**
 * URLs the user explicitly chose to open in Chrome's default viewer.
 * Consumed once so a later visit is intercepted normally again.
 */
const bypassOnce = new Set();
export function bypassNextNavigation(url) {
    bypassOnce.add(url);
}
/** Redirect top-level PDF navigations to the LOOM custom viewer. */
export function initPdfInterceptor() {
    chrome.webNavigation.onBeforeNavigate.addListener((details) => {
        if (details.frameId !== 0)
            return;
        if (!isPdfUrl(details.url))
            return;
        if (bypassOnce.has(details.url)) {
            bypassOnce.delete(details.url);
            return;
        }
        chrome.tabs.update(details.tabId, { url: buildViewerUrl(details.url) }).catch((error) => {
            console.warn("[LOOM] Failed to redirect to PDF viewer:", error);
        });
    });
    console.info("[LOOM] PDF interceptor initialized.");
}
