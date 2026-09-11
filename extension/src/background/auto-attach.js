/**
 * Match upload fields against the recent-document index and fetch cached files.
 */
import { loadSyncConfig } from "./sync-config";
function camelMatch(raw) {
    return {
        documentId: String(raw.documentId ?? raw.document_id),
        filename: String(raw.filename ?? ""),
        docType: String(raw.docType ?? raw.doc_type ?? "other"),
        sourceUrl: String(raw.sourceUrl ?? raw.source_url ?? ""),
        summary: String(raw.summary ?? ""),
        hasFile: Boolean(raw.hasFile ?? raw.has_file),
        confidence: Number(raw.confidence ?? 0),
        reason: String(raw.reason ?? ""),
    };
}
export async function matchUploadField(request) {
    const config = await loadSyncConfig();
    const response = await fetch(`${config.apiBaseUrl}/api/skills/auto-attach/match`, {
        method: "POST",
        headers: {
            Authorization: `Bearer ${config.authToken}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            labelText: request.labelText,
            surroundingText: request.surroundingText,
            fieldName: request.fieldName,
            accept: request.accept,
        }),
    });
    if (!response.ok)
        return null;
    const body = (await response.json());
    if (!body.match)
        return null;
    return camelMatch(body.match);
}
export async function fetchDocumentFile(documentId) {
    const config = await loadSyncConfig();
    const response = await fetch(`${config.apiBaseUrl}/api/skills/auto-attach/documents/${documentId}/file`, { headers: { Authorization: `Bearer ${config.authToken}` } });
    if (!response.ok)
        return null;
    const disposition = response.headers.get("content-disposition") ?? "";
    const filename = disposition.match(/filename="([^"]+)"/)?.[1] ??
        disposition.match(/filename=([^;]+)/)?.[1]?.trim() ??
        "document.bin";
    const mimeType = response.headers.get("content-type") ?? "application/octet-stream";
    return {
        bytes: await response.arrayBuffer(),
        filename,
        mimeType: mimeType.split(";")[0]?.trim() || "application/octet-stream",
    };
}
