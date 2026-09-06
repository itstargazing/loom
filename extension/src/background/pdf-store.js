/**
 * Background-side cache of PDF metadata for documents loaded in viewer tabs.
 *
 * Only extracted text and form-field descriptions are cached here — raw PDF
 * bytes stay in the viewer page, since they are too large to pass over the
 * extension message bus.
 */
class BackgroundPdfStore {
    snapshots = new Map();
    forms = new Map();
    tabToUrl = new Map();
    setLoaded(tabId, snapshot, form) {
        if (tabId !== undefined) {
            this.tabToUrl.set(tabId, snapshot.url);
        }
        this.snapshots.set(snapshot.url, snapshot);
        this.forms.set(snapshot.url, form);
    }
    resolveUrl(tabId, url) {
        if (url)
            return url;
        if (tabId !== undefined)
            return this.tabToUrl.get(tabId);
        return undefined;
    }
    getSnapshot(url) {
        return this.snapshots.get(url);
    }
    getForm(url) {
        return this.forms.get(url);
    }
    removeTab(tabId) {
        this.tabToUrl.delete(tabId);
    }
}
export const backgroundPdfStore = new BackgroundPdfStore();
