/** In-memory registry of loaded PDF documents, keyed by source URL. */
class PdfContentRegistry {
    snapshots = new Map();
    forms = new Map();
    bytes = new Map();
    set(url, pages, numPages, options = {}) {
        const form = options.form ?? {
            url,
            hasFormFields: false,
            fields: [],
        };
        const snapshot = {
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
    getSnapshot(url) {
        return this.snapshots.get(url);
    }
    getForm(url) {
        return this.forms.get(url);
    }
    getBytes(url) {
        return this.bytes.get(url);
    }
    getLatestSnapshot() {
        const entries = [...this.snapshots.values()];
        return entries.at(-1);
    }
    getPageText(url, pageNumber) {
        const snapshot = this.snapshots.get(url);
        if (!snapshot)
            return null;
        const page = snapshot.pages.find((p) => p.pageNumber === pageNumber);
        return page?.text ?? null;
    }
    getAllText(url) {
        const snapshot = this.snapshots.get(url);
        if (!snapshot)
            return "";
        return snapshot.pages.map((p) => p.text).join("\n\n");
    }
    clear(url) {
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
    titleFromUrl(url) {
        try {
            const parsed = new URL(url);
            const name = parsed.pathname.split("/").pop();
            return name ? decodeURIComponent(name) : "PDF Document";
        }
        catch {
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
    getSnapshot(url) {
        return pdfContentRegistry.getSnapshot(url);
    },
    getLatestSnapshot() {
        return pdfContentRegistry.getLatestSnapshot();
    },
    getPageText(url, pageNumber) {
        return pdfContentRegistry.getPageText(url, pageNumber);
    },
    getAllText(url) {
        return pdfContentRegistry.getAllText(url);
    },
    getForm(url) {
        return pdfContentRegistry.getForm(url);
    },
    getBytes(url) {
        return pdfContentRegistry.getBytes(url);
    },
};
