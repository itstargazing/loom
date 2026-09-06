"""Turn free-text dates into datetimes, without inventing a day that was not said.

Sources write "2026-09-15", "October 20, 2026", "next Friday", and "end of term".
The first two resolve; the last stays as `due_text` with no `due_date`.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
US_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
MONTH_DAY_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b",
    re.IGNORECASE,
)
DAY_MONTH_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\.?(?:,?\s+(\d{4}))?\b",
    re.IGNORECASE,
)
NEXT_WEEKDAY_RE = re.compile(
    r"\bnext\s+(" + "|".join(WEEKDAYS) + r")\b",
    re.IGNORECASE,
)
RELATIVE_RE = re.compile(
    r"\b(today|tomorrow|in\s+(\d+)\s+days?)\b",
    re.IGNORECASE,
)


def _aware(year: int, month: int, day: int) -> datetime | None:
    try:
        return datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None


def parse_reference(occurred_at: str | None) -> datetime:
    if occurred_at:
        try:
            parsed = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            pass
    return datetime.now(UTC)


def parse_due(due_text: str, *, occurred_at: str | None = None) -> datetime | None:
    """Resolve a captured date string against the moment it was seen."""
    text = (due_text or "").strip()
    if not text:
        return None
    reference = parse_reference(occurred_at)

    iso = ISO_RE.search(text)
    if iso:
        return _aware(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))

    us = US_RE.search(text)
    if us:
        month, day, year = int(us.group(1)), int(us.group(2)), int(us.group(3))
        if year < 100:
            year += 2000
        return _aware(year, month, day)

    month_day = MONTH_DAY_RE.search(text)
    if month_day:
        month = MONTHS[month_day.group(1).lower().rstrip(".")]
        day = int(month_day.group(2))
        year = int(month_day.group(3)) if month_day.group(3) else reference.year
        resolved = _aware(year, month, day)
        if resolved and resolved.date() < reference.date() and not month_day.group(3):
            resolved = _aware(year + 1, month, day)
        return resolved

    day_month = DAY_MONTH_RE.search(text)
    if day_month:
        day = int(day_month.group(1))
        month = MONTHS[day_month.group(2).lower().rstrip(".")]
        year = int(day_month.group(3)) if day_month.group(3) else reference.year
        resolved = _aware(year, month, day)
        if resolved and resolved.date() < reference.date() and not day_month.group(3):
            resolved = _aware(year + 1, month, day)
        return resolved

    weekday = NEXT_WEEKDAY_RE.search(text)
    if weekday:
        target = WEEKDAYS[weekday.group(1).lower()]
        ahead = (target - reference.weekday()) % 7
        if ahead == 0:
            ahead = 7
        day = (reference + timedelta(days=ahead)).date()
        return datetime(day.year, day.month, day.day, tzinfo=UTC)

    relative = RELATIVE_RE.search(text)
    if relative:
        token = relative.group(1).lower()
        if token == "today":
            delta = 0
        elif token == "tomorrow":
            delta = 1
        else:
            delta = int(relative.group(2))
        day = (reference + timedelta(days=delta)).date()
        return datetime(day.year, day.month, day.day, tzinfo=UTC)

    return None


def date_identity(due_text: str, *, occurred_at: str | None = None) -> str:
    resolved = parse_due(due_text, occurred_at=occurred_at)
    if resolved is not None:
        return resolved.date().isoformat()
    return re.sub(r"\s+", " ", due_text).strip().casefold()
