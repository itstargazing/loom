import { captureEmitter } from "../emitter";
import { labelTextFor, surroundingTextFor } from "../dom-utils";
import { watchDom } from "../dom-watcher";
const UPLOAD_SELECTOR = "input[type='file']";
/**
 * Emits upload_field_detected when a file input appears, including the label and
 * nearby text so Phase 13 can match it against recently seen documents.
 */
export function installUploadFieldSignal() {
    const seen = new WeakSet();
    const report = (input) => {
        if (seen.has(input))
            return;
        seen.add(input);
        captureEmitter.emit("upload_field_detected", {
            fieldName: input.name || null,
            fieldId: input.id || null,
            accept: input.accept || null,
            multiple: input.multiple,
            labelText: labelTextFor(input),
            surroundingText: surroundingTextFor(input),
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
    return unwatchDom;
}
