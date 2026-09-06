import type { PdfDocumentSnapshot, PdfFormSnapshot } from "../pdf/types";

/**
 * Background-side cache of PDF metadata for documents loaded in viewer tabs.
 *
 * Only extracted text and form-field descriptions are cached here — raw PDF
 * bytes stay in the viewer page, since they are too large to pass over the
 * extension message bus.
 */
class BackgroundPdfStore {
  private snapshots = new Map<string, PdfDocumentSnapshot>();
  private forms = new Map<string, PdfFormSnapshot>();
  private tabToUrl = new Map<number, string>();

  setLoaded(
    tabId: number | undefined,
    snapshot: PdfDocumentSnapshot,
    form: PdfFormSnapshot,
  ): void {
    if (tabId !== undefined) {
      this.tabToUrl.set(tabId, snapshot.url);
    }
    this.snapshots.set(snapshot.url, snapshot);
    this.forms.set(snapshot.url, form);
  }

  resolveUrl(tabId?: number, url?: string): string | undefined {
    if (url) return url;
    if (tabId !== undefined) return this.tabToUrl.get(tabId);
    return undefined;
  }

  getSnapshot(url: string): PdfDocumentSnapshot | undefined {
    return this.snapshots.get(url);
  }

  getForm(url: string): PdfFormSnapshot | undefined {
    return this.forms.get(url);
  }

  removeTab(tabId: number): void {
    this.tabToUrl.delete(tabId);
  }
}

export const backgroundPdfStore = new BackgroundPdfStore();
