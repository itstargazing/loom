import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
GlobalWorkerOptions.workerSrc = pdfWorker;
/** Fetch PDF bytes from a remote or file:// URL. */
export async function fetchPdfBytes(url) {
    const response = await fetch(url, { credentials: "include" });
    if (!response.ok) {
        throw new Error(`Failed to fetch PDF (HTTP ${response.status})`);
    }
    return new Uint8Array(await response.arrayBuffer());
}
/** Load a PDF with pdf.js and extract text from every page, preserving page numbers. */
export async function loadPdfDocument(bytes) {
    // pdf.js may transfer ownership of the buffer, so hand it a copy — the caller
    // still needs the original bytes for pdf-lib form access.
    const document = await getDocument({ data: bytes.slice() }).promise;
    const pages = [];
    for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
        const page = await document.getPage(pageNumber);
        const textContent = await page.getTextContent();
        const text = textContent.items
            .map((item) => ("str" in item ? item.str : ""))
            .join(" ")
            .replace(/\s+/g, " ")
            .trim();
        pages.push({ pageNumber, text });
        page.cleanup();
    }
    return { document, pages, numPages: document.numPages };
}
