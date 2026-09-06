/**
 * Unobtrusive confirmation shown when a copy is filed as a citation.
 */
import { clipDetail, showConfirmation } from "./confirmation-overlay";
export function showCitationConfirmation(quote, anchor) {
    showConfirmation("Added to citations", clipDetail(quote), anchor);
}
