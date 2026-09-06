"""Pull actually-read passages out of a scroll_dwell payload.

The classifier may still emit a single ``reading_highlight``; this pass owns
every section that cleared the dwell threshold so headings and dwell times are
preserved rather than discarded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class ExtractedPassage:
    passage: str
    heading: str | None
    dwell_ms: int
    confidence: float


def extract_dwell_passages(
    payload: dict[str, Any],
    *,
    threshold_ms: int | None = None,
) -> list[ExtractedPassage]:
    """Return sections the user lingered on, in page order."""
    threshold = (
        settings.reading_dwell_threshold_ms if threshold_ms is None else threshold_ms
    )
    sections = payload.get("sections") or []
    extracted: list[ExtractedPassage] = []

    for section in sections:
        if not isinstance(section, dict):
            continue
        try:
            dwell_ms = int(section.get("dwellMs") or section.get("dwell_ms") or 0)
        except (TypeError, ValueError):
            continue
        if dwell_ms < threshold:
            continue
        passage = str(section.get("excerpt") or section.get("text") or "").strip()
        if not passage:
            continue
        heading = str(section.get("heading") or "").strip() or None
        #  Longer attention is a stronger signal, capped so a stuck tab cannot
        #  look like a perfect classification.
        confidence = min(0.85, 0.4 + dwell_ms / 120_000)
        extracted.append(
            ExtractedPassage(
                passage=passage,
                heading=heading,
                dwell_ms=dwell_ms,
                confidence=confidence,
            )
        )

    return extracted
