/** Passive capture signal types and payloads. */

export const CAPTURE_EVENT_TYPES = [
  "highlight_selected",
  "text_copied",
  "page_opened",
  "scroll_dwell",
  "upload_field_detected",
] as const;

export type CaptureEventType = (typeof CAPTURE_EVENT_TYPES)[number];

/** Human-readable names, used in the popup settings and debug panel. */
export const CAPTURE_EVENT_LABELS: Record<CaptureEventType, string> = {
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
export const CAPTURE_EVENT_DESCRIPTIONS: Record<CaptureEventType, string> = {
  highlight_selected: "Text you select on a page, plus the paragraph around it.",
  text_copied: "Text you copy, plus the paragraph around it.",
  page_opened: "The readable text of pages and PDFs you open.",
  scroll_dwell: "Which sections of a long page actually held your attention.",
  upload_field_detected: "When a file upload field appears, and its label text.",
};

export interface HighlightSelectedPayload {
  text: string;
  /** Surrounding paragraph the selection sits in. */
  context: string;
}

export interface TextCopiedPayload {
  text: string;
  context: string;
}

export interface PageOpenedPayload {
  contentType: "html" | "pdf";
  fullText: string;
  wordCount: number;
  /** True when fullText was cut off at the extraction limit. */
  truncated: boolean;
  /** Present for PDFs only. */
  pageCount?: number;
}

export interface DwellSection {
  /** Document order of the section within the page. */
  index: number;
  heading: string | null;
  excerpt: string;
  dwellMs: number;
}

export interface ScrollDwellPayload {
  /** Total time any tracked section was visible. */
  totalVisibleMs: number;
  /** Sections that met the dwell threshold, in document order. */
  sections: DwellSection[];
  /** How many sections were tracked overall, met threshold or not. */
  trackedSectionCount: number;
  dwellThresholdMs: number;
}

export interface UploadFieldDetectedPayload {
  fieldName: string | null;
  fieldId: string | null;
  /** The input's accept attribute, if set. */
  accept: string | null;
  multiple: boolean;
  /** Associated <label> text, or nearest preceding text. */
  labelText: string;
  /** Broader text near the field, for matching against recent documents. */
  surroundingText: string;
}

interface CaptureEventEnvelope {
  id: string;
  sourceUrl: string;
  pageTitle: string;
  /** ISO 8601 */
  timestamp: string;
}

export type CaptureEvent =
  | (CaptureEventEnvelope & {
      type: "highlight_selected";
      payload: HighlightSelectedPayload;
    })
  | (CaptureEventEnvelope & { type: "text_copied"; payload: TextCopiedPayload })
  | (CaptureEventEnvelope & { type: "page_opened"; payload: PageOpenedPayload })
  | (CaptureEventEnvelope & { type: "scroll_dwell"; payload: ScrollDwellPayload })
  | (CaptureEventEnvelope & {
      type: "upload_field_detected";
      payload: UploadFieldDetectedPayload;
    });

export type CapturePayloadFor<T extends CaptureEventType> = Extract<
  CaptureEvent,
  { type: T }
>["payload"];

/** Batch message sent from a capture context to the background service worker. */
export interface CaptureBatchMessage {
  type: "capture:events";
  events: CaptureEvent[];
}

/** Snapshot of the in-memory dev feed, served by the background service worker. */
export interface CaptureFeed {
  /** Newest first. */
  events: CaptureEvent[];
  counts: Record<CaptureEventType, number>;
  totalReceived: number;
}
