import { captureEmitter } from "../emitter";
import { extractReadableText } from "../readable-text";
/** Minimum extracted length worth reporting — filters out blank shells. */
const MIN_TEXT_LENGTH = 200;
/**
 * Emits page_opened once a normal web page has settled.
 *
 * PDFs are handled separately: the Phase 1 viewer reports its extracted text to
 * the background service worker, which synthesises the page_opened event from
 * that. This keeps a single extraction path per content type.
 */
export function installPageOpenedSignal() {
    let emitted = false;
    let idleHandle = null;
    const run = () => {
        if (emitted)
            return;
        emitted = true;
        const readable = extractReadableText();
        if (readable.text.length < MIN_TEXT_LENGTH)
            return;
        captureEmitter.emit("page_opened", {
            contentType: "html",
            fullText: readable.text,
            wordCount: readable.wordCount,
            truncated: readable.truncated,
        });
    };
    // Extraction walks the DOM, so defer it until the browser is idle.
    if (typeof requestIdleCallback === "function") {
        idleHandle = requestIdleCallback(run, { timeout: 3000 });
    }
    else {
        idleHandle = window.setTimeout(run, 1000);
    }
    return () => {
        if (idleHandle === null)
            return;
        if (typeof cancelIdleCallback === "function") {
            cancelIdleCallback(idleHandle);
        }
        else {
            clearTimeout(idleHandle);
        }
    };
}
