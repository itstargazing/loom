import type {
  PdfDocumentSnapshot,
  PdfFormSnapshot,
  PdfPageText,
} from "./types";

/** In-memory registry of loaded PDF documents, keyed by source URL. */
class PdfContentRegistry {
  private snapshots = new Map<string, PdfDocumentSnapshot>();
  private forms = new Map<string, PdfFormSnapshot>();
  private bytes = new Map<string, Uint8Array>();

  set(
    url: string,
    pages: PdfPageText[],
    numPages: number,
    options: {
      title?: string;
      usingFallback?: boolean;
      form?: PdfFormSnapshot;
      pdfBytes?: Uint8Array;
    } = {},
  ): PdfDocumentSnapshot {
    const form = options.form ?? {
      url,
      hasFormFields: false,
      fields: [],
    };

    const snapshot: PdfDocumentSnapshot = {
      url,
      title: options.title ?? this.titleFromUrl(url),
      numPages,
      pages,
      loadedAt: new Date().toISOString(),
      usingFallback: options.usingFallback ?? false,
      hasFormFields: form.hasFormFields,
      formFieldCount: form.fields.length,
    };

    this.snapshots.set(url, snapshot);
    this.forms.set(url, form);
    if (options.pdfBytes) {
      this.bytes.set(url, options.pdfBytes);
    }

    return snapshot;
  }

  getSnapshot(url: string): PdfDocumentSnapshot | undefined {
    return this.snapshots.get(url);
  }

  getForm(url: string): PdfFormSnapshot | undefined {
    return this.forms.get(url);
  }

  getBytes(url: string): Uint8Array | undefined {
    return this.bytes.get(url);
  }

  getLatestSnapshot(): PdfDocumentSnapshot | undefined {
    const entries = [...this.snapshots.values()];
    return entries.at(-1);
  }

  getPageText(url: string, pageNumber: number): string | null {
    const snapshot = this.snapshots.get(url);
    if (!snapshot) return null;
    const page = snapshot.pages.find((p) => p.pageNumber === pageNumber);
    return page?.text ?? null;
  }

  getAllText(url: string): string {
    const snapshot = this.snapshots.get(url);
    if (!snapshot) return "";
    return snapshot.pages.map((p) => p.text).join("\n\n");
  }

  clear(url?: string): void {
    if (url) {
      this.snapshots.delete(url);
      this.forms.delete(url);
      this.bytes.delete(url);
      return;
    }
    this.snapshots.clear();
    this.forms.clear();
    this.bytes.clear();
  }

  private titleFromUrl(url: string): string {
    try {
      const parsed = new URL(url);
      const name = parsed.pathname.split("/").pop();
      return name ? decodeURIComponent(name) : "PDF Document";
    } catch {
      return "PDF Document";
    }
  }
}

export const pdfContentRegistry = new PdfContentRegistry();

/**
 * Internal API surface for other extension modules.
 * Access via message bus or direct import within the PDF subsystem.
 */
export const pdfContentApi = {
  getSnapshot(url: string) {
    return pdfContentRegistry.getSnapshot(url);
  },
  getLatestSnapshot() {
    return pdfContentRegistry.getLatestSnapshot();
  },
  getPageText(url: string, pageNumber: number) {
    return pdfContentRegistry.getPageText(url, pageNumber);
  },
  getAllText(url: string) {
    return pdfContentRegistry.getAllText(url);
  },
  getForm(url: string) {
    return pdfContentRegistry.getForm(url);
  },
  getBytes(url: string) {
    return pdfContentRegistry.getBytes(url);
  },
};

export type { PdfDocumentSnapshot, PdfFormSnapshot, PdfPageText };
