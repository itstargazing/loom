/** Shared PDF types and URL helpers used across the extension. */
/** Returns true if the URL likely points to a PDF document. */
export function isPdfUrl(url) {
    if (!url)
        return false;
    const blockedPrefixes = [
        "chrome://",
        "chrome-extension://",
        "edge://",
        "about:",
        "devtools://",
    ];
    if (blockedPrefixes.some((prefix) => url.startsWith(prefix)))
        return false;
    if (url.includes("/src/pdf/viewer.html"))
        return false;
    try {
        const parsed = new URL(url);
        // Covers http(s), file://, and blob: sources ending in .pdf
        if (parsed.pathname.toLowerCase().endsWith(".pdf"))
            return true;
        // Some servers serve PDFs without a .pdf extension.
        if (parsed.searchParams.get("format") === "pdf")
            return true;
    }
    catch {
        return false;
    }
    return false;
}
export function buildViewerUrl(pdfUrl) {
    const viewerBase = chrome.runtime.getURL("src/pdf/viewer.html");
    return `${viewerBase}?src=${encodeURIComponent(pdfUrl)}`;
}
export function parseViewerSrc(viewerUrl) {
    try {
        const url = new URL(viewerUrl);
        return url.searchParams.get("src");
    }
    catch {
        return null;
    }
}
