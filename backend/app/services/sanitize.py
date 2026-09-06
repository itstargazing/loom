"""Strip markup from user-supplied plain-text fields."""

from __future__ import annotations

import re

_TAG_RE = re.compile(r"<[^>]*>")


def sanitize_plain_text(value: str, *, max_len: int = 255) -> str:
    """Remove tags and collapse whitespace. Empty input stays empty."""
    cleaned = _TAG_RE.sub("", value)
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_len]
