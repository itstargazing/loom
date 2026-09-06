import { captureEmitter } from "../emitter";
import { collapseWhitespace, extractContext, truncate } from "../dom-utils";
import { selectionRect } from "../glossary-overlay";

const MIN_LENGTH = 4;
const MAX_LENGTH = 5000;
/** Some pages fire copy twice; ignore an identical repeat within this window. */
const DEDUPE_WINDOW_MS = 2000;

/**
 * Emits text_copied for both keyboard and context-menu copies — the DOM copy
 * event covers each.
 */
export function installCopySignal(
  onCopy?: (eventId: string, rect: DOMRect | null) => void,
): () => void {
  let lastText = "";
  let lastAt = 0;

  const onCopyEvent = (): void => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    const text = collapseWhitespace(selection.toString());
    if (text.length < MIN_LENGTH || text.length > MAX_LENGTH) return;

    const now = Date.now();
    if (text === lastText && now - lastAt < DEDUPE_WINDOW_MS) return;

    // Skip password fields outright — never capture credentials.
    const target = range.commonAncestorContainer;
    const element = target instanceof Element ? target : target.parentElement;
    if (element?.closest("input[type='password']")) return;

    lastText = text;
    lastAt = now;

    const event = captureEmitter.emit("text_copied", {
      text: truncate(text, MAX_LENGTH),
      context: extractContext(range),
    });
    onCopy?.(event.id, selectionRect());
  };

  document.addEventListener("copy", onCopyEvent, { passive: true });

  return () => document.removeEventListener("copy", onCopyEvent);
}
