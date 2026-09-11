/**
 * LOOM background service worker.
 * Handles the message bus between content scripts, the PDF viewer, and the popup.
 */
import { loadCaptureSettings } from "../capture/settings";
import { bypassNextNavigation, initPdfInterceptor } from "../pdf/interceptor";
import { captureBus } from "./capture-bus";
import { backgroundPdfStore } from "./pdf-store";
import { getSyncStatus, initSync, queueForSync, syncNow } from "./sync";
import { fetchDocumentFile, matchUploadField } from "./auto-attach";
import { notifyClassifiedSkills } from "./glossary-notify";
initPdfInterceptor();
initSync();
chrome.runtime.onInstalled.addListener(() => {
    console.info("[LOOM] Extension installed.");
});
chrome.tabs.onRemoved.addListener((tabId) => {
    backgroundPdfStore.removeTab(tabId);
});
/**
 * Turns a PDF load into a page_opened capture event.
 *
 * Content scripts cannot reach the viewer page, so the viewer reports its
 * extracted text here and the background emits the capture event on its behalf.
 */
async function capturePdfAsPageOpened(snapshot) {
    if (snapshot.usingFallback)
        return;
    const settings = await loadCaptureSettings();
    if (!settings.signals.page_opened)
        return;
    const fullText = snapshot.pages.map((page) => page.text).join("\n\n");
    if (fullText.length === 0)
        return;
    const event = {
        id: crypto.randomUUID(),
        type: "page_opened",
        sourceUrl: snapshot.url,
        pageTitle: snapshot.title,
        timestamp: snapshot.loadedAt,
        payload: {
            contentType: "pdf",
            fullText,
            wordCount: fullText.split(/\s+/).length,
            truncated: false,
            pageCount: snapshot.numPages,
        },
    };
    captureBus.ingest([event]);
    void queueForSync([event]);
}
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const tabId = message?.tabId ?? sender.tab?.id;
    switch (message?.type) {
        case "ping":
            sendResponse({ ok: true });
            return true;
        case "capture:events": {
            const events = (message.events ?? []);
            captureBus.ingest(events);
            // Respond only once the events are durably queued. Answering earlier
            // would let Chrome terminate this worker mid-write.
            void queueForSync(events).then(() => {
                sendResponse({ ok: true, received: events.length });
                void notifyClassifiedSkills(events, tabId);
            });
            return true;
        }
        case "capture:get-feed":
            sendResponse({ ok: true, feed: captureBus.getFeed() });
            return true;
        case "capture:clear-feed":
            captureBus.clear();
            sendResponse({ ok: true });
            return true;
        case "sync:get-status":
            void getSyncStatus().then((status) => sendResponse({ ok: true, status }));
            return true;
        case "sync:now":
            void syncNow("manual", true).then((outcome) => sendResponse({ ok: true, outcome }));
            return true;
        case "pdf:loaded": {
            const { snapshot, form } = message;
            backgroundPdfStore.setLoaded(tabId, snapshot, form);
            console.info(`[LOOM] PDF loaded: ${snapshot.title} — ${snapshot.numPages} pages, ` +
                `${snapshot.formFieldCount} form fields` +
                (snapshot.usingFallback ? " (fallback)" : ""));
            void capturePdfAsPageOpened(snapshot).then(() => sendResponse({ ok: true }));
            return true;
        }
        case "pdf:fallback":
            console.warn(`[LOOM] PDF fallback for ${message.url}: ${message.reason}`);
            sendResponse({ ok: true });
            return true;
        case "pdf:open-in-chrome": {
            bypassNextNavigation(message.url);
            if (tabId !== undefined) {
                void chrome.tabs.update(tabId, { url: message.url });
            }
            sendResponse({ ok: true });
            return true;
        }
        case "pdf:get-snapshot": {
            const url = backgroundPdfStore.resolveUrl(tabId, message.url);
            const snapshot = url ? backgroundPdfStore.getSnapshot(url) : undefined;
            sendResponse(snapshot ? { ok: true, snapshot } : { ok: false, error: "No PDF snapshot available" });
            return true;
        }
        case "pdf:get-form": {
            const url = backgroundPdfStore.resolveUrl(tabId, message.url);
            const form = url ? backgroundPdfStore.getForm(url) : undefined;
            sendResponse(form ? { ok: true, form } : { ok: false, error: "No PDF form available" });
            return true;
        }
        case "auto-attach:match": {
            void matchUploadField({
                labelText: String(message.labelText ?? ""),
                surroundingText: String(message.surroundingText ?? ""),
                fieldName: message.fieldName ?? null,
                accept: message.accept ?? null,
            })
                .then((match) => sendResponse({ ok: true, match }))
                .catch((error) => sendResponse({
                ok: false,
                error: error instanceof Error ? error.message : "Match failed",
            }));
            return true;
        }
        case "auto-attach:fetch-file": {
            void fetchDocumentFile(String(message.documentId ?? ""))
                .then((file) => {
                if (!file) {
                    sendResponse({ ok: false, error: "No cached file" });
                    return;
                }
                sendResponse({
                    ok: true,
                    bytes: Array.from(new Uint8Array(file.bytes)),
                    filename: file.filename,
                    mimeType: file.mimeType,
                });
            })
                .catch((error) => sendResponse({
                ok: false,
                error: error instanceof Error ? error.message : "Fetch failed",
            }));
            return true;
        }
        default:
            return false;
    }
});
console.info("[LOOM] Service worker initialized.");
