import { TextLayer } from "pdfjs-dist";
export const DEFAULT_SCALE = 1.25;
export async function renderPageToContainer(pdfDocument, pageNumber, scale, pageContainer) {
    pageContainer.replaceChildren();
    const page = await pdfDocument.getPage(pageNumber);
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement("canvas");
    canvas.className = "pdf-page-canvas";
    const context = canvas.getContext("2d");
    if (!context) {
        throw new Error("Canvas 2D context unavailable");
    }
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    canvas.style.width = `${viewport.width}px`;
    canvas.style.height = `${viewport.height}px`;
    const canvasWrapper = document.createElement("div");
    canvasWrapper.className = "pdf-page-wrapper";
    canvasWrapper.style.width = `${viewport.width}px`;
    canvasWrapper.style.height = `${viewport.height}px`;
    const textLayer = document.createElement("div");
    textLayer.className = "textLayer";
    canvasWrapper.append(canvas, textLayer);
    pageContainer.append(canvasWrapper);
    await page.render({ canvasContext: context, viewport }).promise;
    const textContent = await page.getTextContent();
    const layer = new TextLayer({
        textContentSource: textContent,
        container: textLayer,
        viewport,
    });
    await layer.render();
    return page;
}
export function clampPage(page, numPages) {
    return Math.min(Math.max(1, page), numPages);
}
export function formatPageLabel(current, total) {
    return `${current} / ${total}`;
}
