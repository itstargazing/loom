/** Shared PDF types and URL helpers used across the extension. */

export interface PdfPageText {
  pageNumber: number;
  text: string;
}

export interface PdfDocumentSnapshot {
  url: string;
  title: string;
  numPages: number;
  pages: PdfPageText[];
  loadedAt: string;
  usingFallback: boolean;
  hasFormFields: boolean;
  formFieldCount: number;
}

export type PdfFormFieldType =
  | "text"
  | "checkbox"
  | "dropdown"
  | "date"
  | "signature"
  | "radio"
  | "unknown";

export interface PdfFormField {
  name: string;
  type: PdfFormFieldType;
  value: string | boolean | null;
  options?: string[];
}

export interface PdfFormSnapshot {
  url: string;
  hasFormFields: boolean;
  fields: PdfFormField[];
}

/** Returns true if the URL likely points to a PDF document. */
export function isPdfUrl(url: string): boolean {
  if (!url) return false;

  const blockedPrefixes = [
    "chrome://",
    "chrome-extension://",
    "edge://",
    "about:",
    "devtools://",
  ];
  if (blockedPrefixes.some((prefix) => url.startsWith(prefix))) return false;
  if (url.includes("/src/pdf/viewer.html")) return false;

  try {
    const parsed = new URL(url);

    // Covers http(s), file://, and blob: sources ending in .pdf
    if (parsed.pathname.toLowerCase().endsWith(".pdf")) return true;

    // Some servers serve PDFs without a .pdf extension.
    if (parsed.searchParams.get("format") === "pdf") return true;
  } catch {
    return false;
  }

  return false;
}

export function buildViewerUrl(pdfUrl: string): string {
  const viewerBase = chrome.runtime.getURL("src/pdf/viewer.html");
  return `${viewerBase}?src=${encodeURIComponent(pdfUrl)}`;
}

export function parseViewerSrc(viewerUrl: string): string | null {
  try {
    const url = new URL(viewerUrl);
    return url.searchParams.get("src");
  } catch {
    return null;
  }
}
