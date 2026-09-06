/**
 * Upload a fillable PDF to the form-filler skill over HTTP.
 *
 * PDF bytes stay off the extension message bus; the viewer (which already
 * holds them) posts directly to the API with the sync token.
 */

import { loadBridgeOrigins } from "../bridge/origins";
import { loadSyncConfig } from "../background/sync-config";

export interface FormFillerUploadResult {
  id: string;
  filename: string;
  fieldCount: number;
  dashboardUrl: string;
}

export async function uploadPdfToFormFiller(
  bytes: Uint8Array,
  filename: string,
  sourceUrl: string,
): Promise<FormFillerUploadResult> {
  const config = await loadSyncConfig();
  const form = new FormData();
  form.append(
    "file",
    new Blob([bytes as BlobPart], { type: "application/pdf" }),
    filename,
  );
  form.append("source_url", sourceUrl);

  const response = await fetch(`${config.apiBaseUrl}/api/skills/form-filler/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${config.authToken}` },
    body: form,
  });

  if (!response.ok) {
    let detail = `Upload failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Keep the status fallback.
    }
    throw new Error(detail);
  }

  const created = (await response.json()) as {
    id: string;
    filename: string;
    fieldCount?: number;
    field_count?: number;
  };
  const origins = await loadBridgeOrigins();
  const dashboardOrigin = origins[0] ?? "http://localhost:3000";

  return {
    id: created.id,
    filename: created.filename,
    fieldCount: created.fieldCount ?? created.field_count ?? 0,
    dashboardUrl: `${dashboardOrigin}/skills/form-filler`,
  };
}
