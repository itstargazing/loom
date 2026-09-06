"""Pull every dated obligation out of a page_opened payload.

Classification is allowed one `deadline` item per event (categories cannot
repeat). Syllabi and event pages mention several, so this pass runs after
classification on `page_opened` events and writes one store row per mention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.services.deadline_parse import date_identity, parse_due

DATE_TOKEN = re.compile(
    r"("
    r"\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
    r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?(?:,?\s+\d{4})?"
    r"|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"|(?:today|tomorrow|in\s+\d+\s+days?)"
    r")",
    re.IGNORECASE,
)

DEADLINE_NEARBY = re.compile(
    r"\b(due|deadline|submit|submission|exam|midterm|final|quiz|assignment|"
    r"problem set|homework|essay|paper|rsvp|payable|payment|tuition|"
    r"appl(?:y|ication)|close[sd]?|last day|no later than|by)\b",
    re.IGNORECASE,
)

PAGE_HINTS = re.compile(
    r"\b(syllabus|course|lecture|assignment|exam|midterm|contract|lease|"
    r"event|calendar|schedule|deadline|rsvp|fellowship|application)\b",
    re.IGNORECASE,
)

KIND_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(exam|midterm|final|quiz)\b", re.I), "exam"),
    (re.compile(r"\b(rsvp)\b", re.I), "rsvp"),
    (re.compile(r"\b(payment|payable|tuition|invoice)\b", re.I), "payment_due"),
    (re.compile(r"\b(appl(?:y|ication)|cohort)\b", re.I), "application_due"),
    (
        re.compile(
            r"\b(assignment|problem set|homework|essay|paper|project|due|submit)\b",
            re.I,
        ),
        "assignment_due",
    ),
)

TITLE_BEFORE_DUE = re.compile(
    r"(.+?)\s+(?:is\s+)?(?:due|closes?|close on|must be submitted|no later than|is on)\b",
    re.IGNORECASE,
)
FILENAME_HINT = re.compile(
    r"\.(pdf|html?|docx?)$|(syllabus|v\d+|draft|final|updated)",
    re.IGNORECASE,
)

CONFIRMED_AT = 0.5


@dataclass(frozen=True, slots=True)
class ExtractedDeadline:
    title: str
    due_text: str
    kind: str
    confidence: float
    context_snippet: str


def document_identity(url: str) -> str:
    """Host plus path, minus a filename so syllabus.pdf and syllabus-v2 merge."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").removeprefix("www.").casefold()
    parts = [part for part in parsed.path.split("/") if part]
    if parts and FILENAME_HINT.search(parts[-1]):
        parts = parts[:-1]
    stem = "/".join(parts[:3])
    return f"{host}/{stem}".rstrip("/") if stem else host


def _sentence_around(text: str, start: int, end: int) -> str:
    break_at = {".", "!", "?", "\n"}
    left = start
    while left > 0 and text[left - 1] not in break_at:
        left -= 1
    right = end
    while right < len(text) and text[right] not in break_at:
        right += 1
    return re.sub(r"\s+", " ", text[left:right]).strip(" \t:-")


def _kind_of(sentence: str) -> str:
    for pattern, kind in KIND_RULES:
        if pattern.search(sentence):
            return kind
    return "other"


def _title_of(sentence: str, due_text: str, page_title: str) -> str:
    without_date = sentence.replace(due_text, " ").strip()
    match = TITLE_BEFORE_DUE.search(without_date)
    if match:
        title = match.group(1).strip(" :-")
        title = re.sub(r"^(the|a|an)\s+", "", title, flags=re.I)
        if 3 <= len(title) <= 120:
            return title
    cleaned = re.sub(r"\s+", " ", without_date).strip(" :-")
    cleaned = re.sub(r"\s+(?:is|on|by|at)\s*$", "", cleaned, flags=re.I)
    if 3 <= len(cleaned) <= 120:
        return cleaned
    return page_title or "Untitled deadline"


def _page_looks_relevant(text: str, page_title: str, source_url: str) -> bool:
    haystack = f"{page_title} {source_url} {text[:2_000]}"
    return bool(PAGE_HINTS.search(haystack) or DEADLINE_NEARBY.search(haystack))


def extract_deadlines(
    text: str,
    *,
    page_title: str,
    source_url: str,
    occurred_at: str | None = None,
) -> list[ExtractedDeadline]:
    """Every date on the page that looks like an obligation, in document order."""
    if not text.strip() or not _page_looks_relevant(text, page_title, source_url):
        return []

    seen: set[tuple[str, str]] = set()
    found: list[ExtractedDeadline] = []

    for match in DATE_TOKEN.finditer(text):
        due_text = match.group(0)
        sentence = _sentence_around(text, match.start(), match.end())
        window = text[max(0, match.start() - 80) : match.end() + 80]
        if not DEADLINE_NEARBY.search(window) and not DEADLINE_NEARBY.search(sentence):
            continue

        title = _title_of(sentence, due_text, page_title)
        identity = (
            title.casefold(),
            date_identity(due_text, occurred_at=occurred_at),
        )
        if identity in seen:
            continue
        seen.add(identity)

        resolved = parse_due(due_text, occurred_at=occurred_at)
        confidence = 0.7 if resolved is not None else 0.4
        if not DEADLINE_NEARBY.search(sentence):
            confidence = min(confidence, 0.45)

        found.append(
            ExtractedDeadline(
                title=title,
                due_text=due_text,
                kind=_kind_of(sentence),
                confidence=confidence,
                context_snippet=sentence[:400],
            )
        )

    return found
