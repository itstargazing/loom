/**
 * Message-bus access to PDF content from contexts outside the viewer page
 * (content scripts, popup). Intentionally free of pdf.js and pdf-lib imports so
 * those contexts stay lightweight.
 */

import type { PdfDocumentSnapshot, PdfFormSnapshot } from "./types";

export interface PdfRequestTarget {
  /** Source PDF URL. Omit to resolve from the tab. */
  url?: string;
  /** Tab to resolve against. Required from the popup, where there is no sender tab. */
  tabId?: number;
}

/** Request a PDF's extracted-text snapshot. */
export async function requestPdfSnapshot(
  target: PdfRequestTarget = {},
): Promise<PdfDocumentSnapshot | null> {
  const response = await chrome.runtime.sendMessage({ type: "pdf:get-snapshot", ...target });
  return response?.ok ? (response.snapshot as PdfDocumentSnapshot) : null;
}

/** Request a PDF's form-field snapshot. */
export async function requestPdfForm(
  target: PdfRequestTarget = {},
): Promise<PdfFormSnapshot | null> {
  const response = await chrome.runtime.sendMessage({ type: "pdf:get-form", ...target });
  return response?.ok ? (response.form as PdfFormSnapshot) : null;
}
