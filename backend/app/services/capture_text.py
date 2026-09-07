"""Plain-text views of a capture event for cache keys, embeddings, and digest cards."""

from __future__ import annotations

import re
from typing import Any

_WHITESPACE = re.compile(r"\s+")
_EDGE_PUNCT = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)


def capture_snippet(event_type: str, payload: dict[str, Any] | None) -> str:
    payload = payload or {}
    if event_type in {"highlight_selected", "text_copied"}:
        return str(payload.get("text") or "").strip()
    if event_type == "page_opened":
        return str(payload.get("fullText") or "").strip()[:1_200]
    if event_type == "scroll_dwell":
        sections = payload.get("sections") or []
        if sections:
            return str(sections[0].get("excerpt") or "").strip()
        return ""
    if event_type == "upload_field_detected":
        return str(payload.get("labelText") or payload.get("fieldName") or "").strip()
    return ""


def normalize_snippet(text: str) -> str:
    collapsed = _WHITESPACE.sub(" ", text.casefold()).strip()
    return _EDGE_PUNCT.sub("", collapsed)


def referring_url_from_payload(payload: dict[str, Any] | None) -> str | None:
    payload = payload or {}
    for key in ("referringUrl", "referrer", "referer"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:2048]
    return None
