/**
 * Unobtrusive confirmation shown when a highlight is filed as a glossary term.
 */
import { selectionRect, showConfirmation } from "./confirmation-overlay";
export { selectionRect };
export function showGlossaryConfirmation(term, anchor) {
    showConfirmation("Added to glossary", term, anchor);
}
