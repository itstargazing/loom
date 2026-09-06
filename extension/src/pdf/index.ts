/**
 * Internal API for LOOM's PDF subsystem, for use inside the viewer page.
 *
 * Text access (Phase 1.1):
 *   - getSnapshot / getAllText / getPageText — extracted per-page text
 *
 * Form access (Phase 1.2):
 *   - getFormFields — structured AcroForm field list
 *   - fillFields — write values and return filled PDF bytes
 *   - saveFilledPdf — write values and download the result
 *
 * From contexts other than the viewer page, import `requestPdfSnapshot` /
 * `requestPdfForm` from `./messages` instead, which route through the background
 * service worker and avoid bundling pdf.js and pdf-lib.
 */

import { pdfContentApi } from "./pdf-api";
import {
  downloadPdfBytes,
  extractFormFields,
  fillPdfFormFields,
  filenameFromUrl,
} from "./pdf-form";
import type { PdfFormSnapshot } from "./types";

export const loomPdf = {
  ...pdfContentApi,

  /** Structured form fields for a loaded PDF, or null if not loaded. */
  getFormFields(url: string): PdfFormSnapshot | null {
    return pdfContentApi.getForm(url) ?? null;
  },

  /** Fill fields by name and return the regenerated PDF bytes. */
  async fillFields(
    url: string,
    values: Record<string, string | boolean>,
  ): Promise<Uint8Array> {
    const bytes = pdfContentApi.getBytes(url);
    if (!bytes) {
      throw new Error(`No PDF bytes cached for ${url}`);
    }
    return fillPdfFormFields(bytes, values);
  },

  /** Fill fields and trigger a download of the result. */
  async saveFilledPdf(
    url: string,
    values: Record<string, string | boolean>,
    filename?: string,
  ): Promise<void> {
    const filled = await this.fillFields(url, values);
    downloadPdfBytes(filled, filename ?? `filled-${filenameFromUrl(url)}`);
  },

  /** Read form fields directly from arbitrary PDF bytes (e.g. an upload). */
  readFormFieldsFromBytes(bytes: Uint8Array, url = "memory://upload") {
    return extractFormFields(bytes, url);
  },
};

export { downloadPdfBytes, extractFormFields, filenameFromUrl, fillPdfFormFields };
export * from "./messages";
export * from "./types";
