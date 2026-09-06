import { loomPdf } from "./index";
import { uploadPdfToFormFiller } from "./form-filler-upload";
import { pdfContentRegistry } from "./pdf-api";
import { extractFormFields, filenameFromUrl } from "./pdf-form";
import { fetchPdfBytes, loadPdfDocument } from "./pdf-loader";
import { parseViewerSrc } from "./types";
import { clampPage, DEFAULT_SCALE, formatPageLabel, renderPageToContainer, } from "./viewer-render";
let pdfDocument = null;
let pdfBytes = null;
let sourceUrl = "";
let currentPage = 1;
let scale = DEFAULT_SCALE;
let numPages = 0;
function getElements() {
    return {
        formBanner: document.getElementById("form-banner"),
        formBannerText: document.getElementById("form-banner-text"),
        formBannerAdd: document.getElementById("form-banner-add"),
        formBannerLink: document.getElementById("form-banner-link"),
        fallbackBanner: document.getElementById("fallback-banner"),
        fallbackReason: document.getElementById("fallback-reason"),
        fallbackLink: document.getElementById("fallback-link"),
        btnPrev: document.getElementById("btn-prev"),
        btnNext: document.getElementById("btn-next"),
        btnZoomIn: document.getElementById("btn-zoom-in"),
        btnZoomOut: document.getElementById("btn-zoom-out"),
        btnFitWidth: document.getElementById("btn-fit-width"),
        pageIndicator: document.getElementById("page-indicator"),
        zoomIndicator: document.getElementById("zoom-indicator"),
        docTitle: document.getElementById("doc-title"),
        loading: document.getElementById("loading"),
        pageContainer: document.getElementById("page-container"),
    };
}
function showFallback(reason) {
    const el = getElements();
    el.fallbackBanner.classList.remove("hidden");
    el.fallbackReason.textContent = reason;
    // Route through the background so the interceptor lets this navigation through
    // instead of redirecting straight back to this viewer.
    el.fallbackLink.href = sourceUrl;
    el.fallbackLink.addEventListener("click", (event) => {
        event.preventDefault();
        void chrome.runtime.sendMessage({ type: "pdf:open-in-chrome", url: sourceUrl });
    });
}
function hideLoading() {
    getElements().loading.classList.add("hidden");
    getElements().pageContainer.classList.remove("hidden");
}
function showFormBanner(fieldCount) {
    const el = getElements();
    el.formBanner.classList.remove("hidden");
    el.formBannerText.textContent = `This document has ${fieldCount} fillable ${fieldCount === 1 ? "field" : "fields"}. Add it to Form Filler to batch-fill from a profile.`;
    el.formBannerAdd.disabled = false;
    el.formBannerAdd.classList.remove("hidden");
    el.formBannerLink.classList.add("hidden");
}
async function addCurrentPdfToFormFiller() {
    const el = getElements();
    if (!pdfBytes) {
        el.formBannerText.textContent = "PDF bytes are not available in this viewer.";
        return;
    }
    el.formBannerAdd.disabled = true;
    el.formBannerText.textContent = "Uploading to Form Filler…";
    try {
        const result = await uploadPdfToFormFiller(pdfBytes, filenameFromUrl(sourceUrl), sourceUrl);
        el.formBannerText.textContent = `Added ${result.filename} (${result.fieldCount} fields).`;
        el.formBannerAdd.classList.add("hidden");
        el.formBannerLink.href = result.dashboardUrl;
        el.formBannerLink.classList.remove("hidden");
    }
    catch (error) {
        el.formBannerAdd.disabled = false;
        el.formBannerText.textContent =
            error instanceof Error ? error.message : "Could not upload this PDF.";
    }
}
function updateControls() {
    const el = getElements();
    el.pageIndicator.textContent = numPages > 0 ? formatPageLabel(currentPage, numPages) : "—";
    el.zoomIndicator.textContent = `${Math.round(scale * 100)}%`;
    el.btnPrev.disabled = currentPage <= 1;
    el.btnNext.disabled = currentPage >= numPages;
}
async function renderCurrentPage() {
    if (!pdfDocument)
        return;
    const el = getElements();
    currentPage = clampPage(currentPage, numPages);
    await renderPageToContainer(pdfDocument, currentPage, scale, el.pageContainer);
    updateControls();
}
async function notifyBackground(snapshot, form) {
    const tab = await chrome.tabs.getCurrent();
    await chrome.runtime.sendMessage({
        type: "pdf:loaded",
        snapshot,
        form,
        tabId: tab?.id,
    });
}
async function loadDocument(url) {
    sourceUrl = url;
    const el = getElements();
    el.docTitle.textContent = filenameFromUrl(url);
    try {
        pdfBytes = await fetchPdfBytes(url);
        const loaded = await loadPdfDocument(pdfBytes);
        pdfDocument = loaded.document;
        numPages = loaded.numPages;
        currentPage = 1;
        const form = await extractFormFields(pdfBytes, url);
        const snapshot = pdfContentRegistry.set(url, loaded.pages, numPages, {
            title: filenameFromUrl(url),
            usingFallback: false,
            form,
            pdfBytes,
        });
        await notifyBackground(snapshot, form);
        if (form.hasFormFields) {
            showFormBanner(form.fields.length);
        }
        hideLoading();
        await renderCurrentPage();
    }
    catch (error) {
        const reason = error instanceof Error ? error.message : "Unknown error";
        console.error("[LOOM PDF] Render failed:", error);
        const emptySnapshot = pdfContentRegistry.set(url, [], 0, {
            title: filenameFromUrl(url),
            usingFallback: true,
        });
        await notifyBackground(emptySnapshot, {
            url,
            hasFormFields: false,
            fields: [],
        });
        await chrome.runtime.sendMessage({
            type: "pdf:fallback",
            url,
            reason,
        });
        showFallback(reason);
        el.loading.innerHTML =
            "<p>Could not load PDF. Use the link above to open in Chrome's viewer.</p>";
    }
}
async function fitToWidth() {
    if (!pdfDocument)
        return;
    const page = await pdfDocument.getPage(currentPage);
    const unscaled = page.getViewport({ scale: 1 });
    const available = getElements().pageContainer.parentElement?.clientWidth ?? unscaled.width;
    scale = Math.max(0.5, Math.min(3, (available - 48) / unscaled.width));
    page.cleanup();
    await renderCurrentPage();
}
function bindControls() {
    const el = getElements();
    el.btnPrev.addEventListener("click", async () => {
        currentPage -= 1;
        await renderCurrentPage();
    });
    el.btnNext.addEventListener("click", async () => {
        currentPage += 1;
        await renderCurrentPage();
    });
    el.btnZoomIn.addEventListener("click", async () => {
        scale = Math.min(3, scale + 0.25);
        await renderCurrentPage();
    });
    el.btnZoomOut.addEventListener("click", async () => {
        scale = Math.max(0.5, scale - 0.25);
        await renderCurrentPage();
    });
    el.btnFitWidth.addEventListener("click", () => {
        void fitToWidth();
    });
    el.formBannerAdd.addEventListener("click", () => {
        void addCurrentPdfToFormFiller();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft" || event.key === "PageUp") {
            event.preventDefault();
            void (async () => {
                currentPage -= 1;
                await renderCurrentPage();
            })();
        }
        if (event.key === "ArrowRight" || event.key === "PageDown") {
            event.preventDefault();
            void (async () => {
                currentPage += 1;
                await renderCurrentPage();
            })();
        }
    });
}
async function init() {
    bindControls();
    const src = parseViewerSrc(window.location.href);
    if (!src) {
        showFallback("No PDF source URL provided.");
        getElements().loading.textContent = "Missing PDF source.";
        return;
    }
    await loadDocument(src);
}
void init();
/** Dev-only: expose the internal PDF API for debugging in the viewer context. */
if (import.meta.env.DEV) {
    window.loomPdf = loomPdf;
}
