import { captureEmitter } from "../emitter";
import { collapseWhitespace, extractContext, truncate } from "../dom-utils";
import { selectionRect } from "../glossary-overlay";

/** Wait for the selection to settle before reading it. */
const SETTLE_MS = 400;
/** Short enough to catch acronyms like "OAuth"; long enough to skip clicks. */
const MIN_LENGTH = 3;
const MAX_LENGTH = 5000;

/**
 * Emits highlight_selected on ordinary text selection.
 *
 * Uses the native selection rather than any custom UI, so the user's reading
 * flow is untouched. The selection rectangle is remembered so a later glossary
 * confirmation can appear next to the highlight.
 */
export function installHighlightSignal(
  onHighlight?: (eventId: string, rect: DOMRect | null) => void,
): () => void {
  let settleTimer: ReturnType<typeof setTimeout> | null = null;
  let lastText = "";

  const readSelection = (): void => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    const text = collapseWhitespace(selection.toString());

    if (text.length < MIN_LENGTH || text.length > MAX_LENGTH) return;
    // selectionchange fires repeatedly while dragging; only emit on change.
    if (text === lastText) return;

    // Ignore selections inside inputs — usually the user editing their own text.
    const target = range.commonAncestorContainer;
    const element = target instanceof Element ? target : target.parentElement;
    if (element?.closest("input, textarea, [contenteditable='true']")) return;

    lastText = text;
    const event = captureEmitter.emit("highlight_selected", {
      text: truncate(text, MAX_LENGTH),
      context: extractContext(range),
    });
    onHighlight?.(event.id, selectionRect());
  };

  const onSelectionChange = (): void => {
    if (settleTimer !== null) clearTimeout(settleTimer);
    settleTimer = setTimeout(() => {
      settleTimer = null;
      readSelection();
    }, SETTLE_MS);
  };

  document.addEventListener("selectionchange", onSelectionChange, { passive: true });

  return () => {
    if (settleTimer !== null) clearTimeout(settleTimer);
    document.removeEventListener("selectionchange", onSelectionChange);
  };
}
