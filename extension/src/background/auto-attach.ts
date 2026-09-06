/**
 * Match upload fields against the recent-document index and fetch cached files.
 */

import { loadSyncConfig } from "./sync-config";

export interface MatchRequest {
  labelText: string;
  surroundingText: string;
  fieldName: string | null;
  accept: string | null;
}

export interface MatchResult {
  documentId: string;
  filename: string;
  docType: string;
  sourceUrl: string;
  summary: string;
  hasFile: boolean;
  confidence: number;
  reason: string;
}

interface MatchResponse {
  match: MatchResult | null;
  candidates: MatchResult[];
}

function camelMatch(raw: Record<string, unknown>): MatchResult {
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

export async function matchUploadField(
  request: MatchRequest,
): Promise<MatchResult | null> {
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
  if (!response.ok) return null;
  const body = (await response.json()) as MatchResponse & {
    match?: Record<string, unknown> | null;
  };
  if (!body.match) return null;
  return camelMatch(body.match as unknown as Record<string, unknown>);
}

export async function fetchDocumentFile(
  documentId: string,
): Promise<{ bytes: ArrayBuffer; filename: string; mimeType: string } | null> {
  const config = await loadSyncConfig();
  const response = await fetch(
    `${config.apiBaseUrl}/api/skills/auto-attach/documents/${documentId}/file`,
    { headers: { Authorization: `Bearer ${config.authToken}` } },
  );
  if (!response.ok) return null;
  const disposition = response.headers.get("content-disposition") ?? "";
  const filename =
    disposition.match(/filename="([^"]+)"/)?.[1] ??
    disposition.match(/filename=([^;]+)/)?.[1]?.trim() ??
    "document.bin";
  const mimeType = response.headers.get("content-type") ?? "application/octet-stream";
  return {
    bytes: await response.arrayBuffer(),
    filename,
    mimeType: mimeType.split(";")[0]?.trim() || "application/octet-stream",
  };
}
