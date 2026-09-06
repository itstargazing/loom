/** Passive capture signal types and payloads. */
export const CAPTURE_EVENT_TYPES = [
    "highlight_selected",
    "text_copied",
    "page_opened",
    "scroll_dwell",
    "upload_field_detected",
];
/** Human-readable names, used in the popup settings and debug panel. */
export const CAPTURE_EVENT_LABELS = {
    highlight_selected: "Highlights",
    text_copied: "Copies",
    page_opened: "Page content",
    scroll_dwell: "Reading attention",
    upload_field_detected: "Upload fields",
};
/**
 * Plain-language descriptions of exactly what each toggle captures.
 * Reused verbatim in the Chrome Web Store listing (Phase 17).
 */
export const CAPTURE_EVENT_DESCRIPTIONS = {
    highlight_selected: "Text you select on a page, plus the paragraph around it.",
    text_copied: "Text you copy, plus the paragraph around it.",
    page_opened: "The readable text of pages and PDFs you open.",
    scroll_dwell: "Which sections of a long page actually held your attention.",
    upload_field_detected: "When a file upload field appears, and its label text.",
};
