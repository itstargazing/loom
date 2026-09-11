/**
 * Turn API error bodies into short, user-facing messages.
 * Never dump raw Pydantic / FastAPI validation payloads into the UI.
 */

export type ApiErrorBody = {
  detail?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function looksLikeRawValidation(text: string): boolean {
  const lower = text.toLowerCase();
  return (
    lower.includes("validation error") ||
    lower.includes("for further information visit") ||
    lower.includes("pydantic") ||
    lower.includes("traceback") ||
    lower.includes("field required") ||
    (lower.includes("type=") && lower.includes("loc="))
  );
}

/**
 * Prefer structured `{ message }` details from the API; otherwise fall back.
 * Raw validation dumps are replaced with the fallback.
 */
export function apiErrorMessage(body: unknown, fallback: string): string {
  if (!isRecord(body)) return fallback;
  const detail = body.detail;

  if (typeof detail === "string") {
    const trimmed = detail.trim();
    if (!trimmed || looksLikeRawValidation(trimmed)) return fallback;
    return trimmed;
  }

  if (isRecord(detail)) {
    const message = detail.message;
    if (typeof message === "string" && message.trim()) {
      return message.trim();
    }
    return fallback;
  }

  if (Array.isArray(detail)) {
    return fallback;
  }

  return fallback;
}

export function apiErrorFields(body: unknown): string[] {
  if (!isRecord(body) || !isRecord(body.detail)) return [];
  const fields = body.detail.fields;
  if (!Array.isArray(fields)) return [];
  return fields.filter((item): item is string => typeof item === "string");
}

export function apiErrorCode(body: unknown): string | null {
  if (!isRecord(body) || !isRecord(body.detail)) return null;
  return typeof body.detail.code === "string" ? body.detail.code : null;
}
