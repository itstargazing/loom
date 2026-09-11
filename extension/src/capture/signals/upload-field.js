import { captureEmitter } from "../emitter";
import { dismissAutoAttachPrompt, showAutoAttachPrompt, } from "../auto-attach-overlay";
import { labelTextFor, surroundingTextFor } from "../dom-utils";
import { watchDom } from "../dom-watcher";
const UPLOAD_SELECTOR = "input[type='file']";
const FIELD_KEY_ATTR = "data-loom-field-key";
const inputsByKey = new Map();
/**
 * Emits upload_field_detected when a file input appears, including the label and
 * nearby text so Phase 13 can match it against recently seen documents.
 *
 * Also asks the background for a suggestion and shows an interactive prompt —
 * never attaching until the user confirms.
 */
export function installUploadFieldSignal() {
    const seen = new WeakSet();
    const report = (input) => {
        if (seen.has(input))
            return;
        seen.add(input);
        const fieldKey = crypto.randomUUID();
        input.setAttribute(FIELD_KEY_ATTR, fieldKey);
        inputsByKey.set(fieldKey, input);
        const labelText = labelTextFor(input);
        const surroundingText = surroundingTextFor(input);
        const fieldName = input.name || null;
        const accept = input.accept || null;
        captureEmitter.emit("upload_field_detected", {
            fieldName,
            fieldId: input.id || null,
            accept,
            multiple: input.multiple,
            labelText,
            surroundingText,
        });
        void chrome.runtime
            .sendMessage({
            type: "auto-attach:match",
            labelText,
            surroundingText,
            fieldName,
            accept,
        })
            .then((response) => {
            if (!response?.ok || !response.match)
                return;
            const rect = input.getBoundingClientRect();
            showAutoAttachPrompt({
                fieldKey,
                documentId: response.match.documentId,
                filename: response.match.filename,
                confidence: response.match.confidence,
                reason: response.match.reason,
                hasFile: response.match.hasFile,
            }, rect, async () => {
                const target = inputsByKey.get(fieldKey);
                if (!target || !response.match.hasFile)
                    return;
                const fileResponse = await chrome.runtime.sendMessage({
                    type: "auto-attach:fetch-file",
                    documentId: response.match.documentId,
                });
                if (!fileResponse?.ok || !fileResponse.bytes)
                    return;
                const bytes = fileResponse.bytes;
                const file = new File([new Uint8Array(bytes)], String(fileResponse.filename ?? response.match.filename), { type: String(fileResponse.mimeType ?? "application/octet-stream") });
                const transfer = new DataTransfer();
                transfer.items.add(file);
                target.files = transfer.files;
                target.dispatchEvent(new Event("input", { bubbles: true }));
                target.dispatchEvent(new Event("change", { bubbles: true }));
            }, () => {
                /* dismissed */
            });
        })
            .catch(() => {
            /* Backend offline — capture still recorded. */
        });
    };
    const scan = (elements) => {
        for (const element of elements) {
            if (element instanceof HTMLInputElement)
                report(element);
        }
    };
    scan(document.querySelectorAll(UPLOAD_SELECTOR));
    const unwatchDom = watchDom((added) => {
        for (const element of added) {
            if (element.matches(UPLOAD_SELECTOR))
                scan([element]);
            scan(element.querySelectorAll(UPLOAD_SELECTOR));
        }
    });
    return () => {
        unwatchDom();
        dismissAutoAttachPrompt();
        inputsByKey.clear();
    };
}
