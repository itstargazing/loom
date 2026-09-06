/**
 * Message-bus access to PDF content from contexts outside the viewer page
 * (content scripts, popup). Intentionally free of pdf.js and pdf-lib imports so
 * those contexts stay lightweight.
 */
/** Request a PDF's extracted-text snapshot. */
export async function requestPdfSnapshot(target = {}) {
    const response = await chrome.runtime.sendMessage({ type: "pdf:get-snapshot", ...target });
    return response?.ok ? response.snapshot : null;
}
/** Request a PDF's form-field snapshot. */
export async function requestPdfForm(target = {}) {
    const response = await chrome.runtime.sendMessage({ type: "pdf:get-form", ...target });
    return response?.ok ? response.form : null;
}
