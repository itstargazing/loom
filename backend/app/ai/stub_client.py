"""Offline classifier used when no model provider is configured.

Keyword heuristics, not a model. It exists so the whole pipeline runs and can be
tested without network access or an API key, and it is deliberately conservative:
it returns 'none' whenever nothing obvious matches. Its accuracy is not
comparable to the cloud path, and the dashboard labels output produced by it.

It reads ``request.context`` rather than the rendered prompt, which is why
:class:`JsonCompletionRequest` carries the structured event alongside the text.
"""

import hashlib
import json
import re
from typing import Any

from app.ai.base import AIClient, JsonCompletion, JsonCompletionRequest, TextCompletionRequest
from app.schemas.classification import (
    ClassificationItem,
    ClassificationResult,
    ExtractedFields,
    SpecField,
)
from app.services.product_extract import extract_product_price, extract_product_specs

#  A short highlight is far more likely to be a term than a sentence.
GLOSSARY_MAX_WORDS = 5
GLOSSARY_STOPWORDS = {
    "the",
    "and",
    "this",
    "that",
    "with",
    "from",
    "your",
    "have",
    "been",
    "will",
    "just",
    "more",
    "than",
}


def _definition_from_context(term: str, context: str) -> str:
    """Prefer the sentence that actually contains the term."""
    if not context.strip():
        return f"A term encountered while reading: {term}."

    sentences = re.split(r"(?<=[.!?])\s+", context.strip())
    needle = term.casefold()
    for sentence in sentences:
        if needle in sentence.casefold():
            return sentence.strip()
    return context.strip()[:400]


CITATION_HINTS = re.compile(
    r"\b(according to|study|research|found that|percent|%|journal|et al\.?|"
    r"survey|report(?:ed|s)?|data show)\b",
    re.IGNORECASE,
)
SCHOLARLY_HOSTS = re.compile(
    r"(arxiv|jstor|pubmed|ncbi|nature|sciencedirect|springer|acm\.org|ieee|"
    r"doi\.org|scholar\.google|\.edu)",
    re.IGNORECASE,
)
CASUAL_COPY = re.compile(
    r"^(lol|lmao|haha|ok|okay|yeah|yep|nah|hey|hi|thanks|ty|omg|see you)\b",
    re.IGNORECASE,
)
CODE_COPY = re.compile(
    r"\b(function|const |let |var |import |export |def |class |return )\b|[{};]{2,}",
)
URL_ONLY = re.compile(r"^https?://\S+$", re.IGNORECASE)
AUTHOR_ACCORDING_TO = re.compile(
    r"according to ([A-Z][A-Za-z'.\-]+(?:\s+[A-Z][A-Za-z'.\-]+){0,3})",
)
AUTHOR_ET_AL = re.compile(
    r"\b([A-Z][A-Za-z'.\-]+(?:\s+[A-Z][A-Za-z'.\-]+){0,2})\s+et al",
)
MIN_CITATION_WORDS = 8
DEADLINE_HINTS = re.compile(
    r"\b(due|deadline|submit by|no later than|rsvp|expires?|payable by|"
    r"last day)\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}"
    r"(?:,?\s+\d{4})?)\b",
    re.IGNORECASE,
)
JOB_HINTS = re.compile(
    r"\b(hiring|apply now|job description|responsibilities|qualifications|"
    r"salary|per annum|full-time|internship)\b",
    re.IGNORECASE,
)
PRODUCT_HINTS = re.compile(
    r"(\$\s?\d|\bprice\b|\badd to cart\b|\bin stock\b|\bfree shipping\b)",
    re.IGNORECASE,
)
CONTRACT_HINTS = re.compile(
    r"\b(shall|hereby|liability|indemnif\w+|terminate this agreement|warrant\w*|"
    r"governing law|arbitration)\b",
    re.IGNORECASE,
)
SENSITIVE_HINTS = re.compile(
    r"\b(password|passwd|api[_ -]?key|secret[_ -]?key|cvv|social security|"
    r"credit card)\b",
    re.IGNORECASE,
)

PRICE_PATTERN = re.compile(r"[$€£]\s?\d[\d,.]*")


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0) if match else None


def _publisher_from_url(source_url: str) -> str | None:
    host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", source_url)).split("/")[0]
    return host or None


def _author_from_text(text: str) -> str | None:
    et_al = AUTHOR_ET_AL.search(text)
    if et_al:
        return f"{et_al.group(1).strip()} et al."
    according = AUTHOR_ACCORDING_TO.search(text)
    if according:
        name = according.group(1).strip()
        if name.casefold() not in {"the study", "the report", "the paper", "research"}:
            return name
    return None


CLAIM_NUMBER = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|percent|degrees?|°C|celsius)?\b",
    re.IGNORECASE,
)
CLAIM_TOPIC_STOP = {
    "according",
    "study",
    "research",
    "participants",
    "showed",
    "found",
    "that",
    "with",
    "from",
    "were",
    "was",
    "have",
    "been",
    "this",
    "their",
    "there",
    "relative",
    "across",
}


TOPIC_AFTER_FIGURE = re.compile(
    r"\b(?:in|of|for)\s+([A-Za-z][A-Za-z\-]+(?:\s+[A-Za-z][A-Za-z\-]+){0,2})"
    r"(?=\s+(?:across|over|during|in|on|at|from|to|relative)\b|[.,;:]|$)",
    re.IGNORECASE,
)


def _topic_from_claim(text: str) -> str:
    """Short topic label for clustering — content words, not the whole sentence."""
    number = CLAIM_NUMBER.search(text)
    if number:
        #  "14 percent decline in working memory" → prefer the noun phrase after
        #  the figure when present; otherwise the nouns just before it.
        after = TOPIC_AFTER_FIGURE.search(text[number.end() :])
        if after:
            return after.group(1).casefold()
        before = text[: number.start()]
        near = [
            word
            for word in re.findall(r"[A-Za-z][A-Za-z\-]+", before)
            if word.casefold() not in CLAIM_TOPIC_STOP and len(word) > 2
        ]
        if len(near) >= 2:
            return " ".join(near[-4:]).casefold()

    words = [
        word
        for word in re.findall(r"[A-Za-z][A-Za-z\-]+", text)
        if word.casefold() not in CLAIM_TOPIC_STOP and len(word) > 2
    ]
    if not words:
        return "general claim"
    return " ".join(words[:5]).casefold()


def _contradiction_candidate(text: str, source_url: str) -> ClassificationItem | None:
    """A checkable figure or factual claim worth pairing against other sources."""
    stripped = text.strip()
    if len(stripped.split()) < MIN_CITATION_WORDS:
        return None
    if not CLAIM_NUMBER.search(stripped):
        return None
    if not (CITATION_HINTS.search(stripped) or SCHOLARLY_HOSTS.search(source_url)):
        return None
    return ClassificationItem(
        category="contradiction_candidate",
        confidence=0.45,
        reason="Checkable figure in an authoritative-sounding claim.",
        fields=ExtractedFields.of(claim=stripped, topic=_topic_from_claim(stripped)),
    )


def _looks_citable(text: str, source_url: str) -> bool:
    """A copied sentence worth citing, not a password, URL, or chat message."""
    stripped = text.strip()
    word_count = len(stripped.split())
    if word_count < MIN_CITATION_WORDS:
        return False
    if URL_ONLY.match(stripped) or CASUAL_COPY.match(stripped) or CODE_COPY.search(stripped):
        return False
    looks_scholarly = bool(SCHOLARLY_HOSTS.search(source_url))
    return looks_scholarly or bool(CITATION_HINTS.search(stripped))


def _citation_fields(
    text: str, context: str, source_url: str, page_title: str
) -> ExtractedFields:
    haystack = f"{text} {context}"
    return ExtractedFields.of(
        quote=text,
        author=_author_from_text(haystack),
        work_title=page_title or None,
        publisher=_publisher_from_url(source_url),
        published_date=_first_match(DATE_PATTERN, haystack),
    )


def _classify_selection(
    text: str, context: str, source_url: str, page_title: str
) -> list[ClassificationItem]:
    """Handle highlight_selected and text_copied."""
    items: list[ClassificationItem] = []
    word_count = len(text.split())
    looks_like_term = (
        1 <= word_count <= GLOSSARY_MAX_WORDS
        and len(text) >= 3
        and text.casefold() not in GLOSSARY_STOPWORDS
        and not text.endswith((".", "?", "!"))
    )

    if looks_like_term:
        items.append(
            ClassificationItem(
                category="glossary_term",
                confidence=0.45,
                reason="Short highlight, matched by keyword heuristics only.",
                fields=ExtractedFields.of(
                    term=text,
                    definition=_definition_from_context(text, context),
                ),
            )
        )

    looks_scholarly = bool(SCHOLARLY_HOSTS.search(source_url))
    if _looks_citable(text, source_url):
        items.append(
            ClassificationItem(
                category="citation",
                confidence=0.5 if looks_scholarly else 0.35,
                reason="Authoritative-sounding phrasing or scholarly source host.",
                fields=_citation_fields(text, context, source_url, page_title),
            )
        )

    claim_item = _contradiction_candidate(text, source_url)
    if claim_item is not None:
        items.append(claim_item)

    date = _first_match(DATE_PATTERN, f"{text} {context}")
    if date and DEADLINE_HINTS.search(f"{text} {context}"):
        title = text.strip() if word_count <= 24 else (page_title or text[:120]).strip()
        kind = (
            "assignment_due"
            if re.search(r"\b(paper|assignment|essay|homework|project)\b", text, re.I)
            else "exam"
            if re.search(r"\b(exam|midterm|final)\b", text, re.I)
            else "other"
        )
        items.append(
            ClassificationItem(
                category="deadline",
                confidence=0.55,
                reason="Selection contains a date and deadline wording.",
                fields=ExtractedFields.of(
                    deadline_title=title or "Untitled deadline",
                    deadline_date=date,
                    deadline_kind=kind,  # type: ignore[arg-type]
                ),
            )
        )

    if word_count > GLOSSARY_MAX_WORDS and not items:
        items.append(
            ClassificationItem(
                category="reading_highlight",
                confidence=0.4,
                reason="Longer passage with no more specific category matched.",
                fields=ExtractedFields.of(passage=text),
            )
        )

    return items


def _classify_page(text: str, page_title: str) -> list[ClassificationItem]:
    """Handle page_opened."""
    items: list[ClassificationItem] = []

    date = _first_match(DATE_PATTERN, text)
    if date and DEADLINE_HINTS.search(text):
        items.append(
            ClassificationItem(
                category="deadline",
                confidence=0.4,
                reason="Page contains both a date and deadline wording.",
                fields=ExtractedFields.of(
                    deadline_title=page_title or "Untitled deadline",
                    deadline_date=date,
                    deadline_kind="other",
                ),
            )
        )

    if JOB_HINTS.search(text):
        items.append(
            ClassificationItem(
                category="job_listing",
                confidence=0.35,
                reason="Page uses job posting vocabulary.",
                fields=ExtractedFields.of(job_title=page_title or "Untitled role"),
            )
        )
    elif PRODUCT_HINTS.search(text):
        items.append(
            ClassificationItem(
                category="product_listing",
                confidence=0.35,
                reason="Page shows a price or cart affordance.",
                fields=ExtractedFields.of(
                    product_name=page_title or "Untitled product",
                    price=extract_product_price(text) or _first_match(PRICE_PATTERN, text),
                    specs=[
                        SpecField(name=key, value=value)
                        for key, value in extract_product_specs(text).items()
                    ]
                    or None,
                ),
            )
        )

    if CONTRACT_HINTS.search(text):
        items.append(
            ClassificationItem(
                category="contract_clause",
                confidence=0.3,
                reason="Page uses contractual language.",
                fields=ExtractedFields.of(
                    clause_text=text[:1_000],
                    flag_reason="Contains contractual language; needs human review.",
                    risk_level="low",
                ),
            )
        )

    return items


def _classify_dwell(payload: dict[str, Any]) -> list[ClassificationItem]:
    """Handle scroll_dwell: the longest-read section becomes a highlight."""
    sections = payload.get("sections") or []
    if not sections:
        return []

    longest = max(sections, key=lambda section: section.get("dwellMs", 0))
    passage = str(longest.get("excerpt", "")).strip()
    if not passage:
        return []

    return [
        ClassificationItem(
            category="reading_highlight",
            confidence=0.5,
            reason="Section held attention longest on the page.",
            fields=ExtractedFields.of(passage=passage),
        )
    ]


def classify_locally(context: dict[str, Any]) -> ClassificationResult:
    """Heuristic classification of one capture event."""
    event_type = str(context.get("eventType", ""))
    payload: dict[str, Any] = context.get("payload") or {}
    source_url = str(context.get("sourceUrl", ""))
    page_title = str(context.get("pageTitle", ""))

    haystack = " ".join(
        str(value) for value in payload.values() if isinstance(value, str)
    )
    if SENSITIVE_HINTS.search(haystack):
        return ClassificationResult(
            classifications=[
                ClassificationItem(
                    category="none",
                    confidence=0.9,
                    reason="Content looks sensitive; skipped.",
                    fields=ExtractedFields.of(),
                )
            ]
        )

    if event_type in {"highlight_selected", "text_copied"}:
        items = _classify_selection(
            str(payload.get("text", "")).strip(),
            str(payload.get("context", "")).strip(),
            source_url,
            page_title,
        )
    elif event_type == "page_opened":
        items = _classify_page(str(payload.get("fullText", "")), page_title)
    elif event_type == "scroll_dwell":
        items = _classify_dwell(payload)
    else:
        # upload_field_detected carries no classifiable content of its own.
        items = []

    if not items:
        items = [
            ClassificationItem(
                category="none",
                confidence=0.6,
                reason="No heuristic matched this event.",
                fields=ExtractedFields.of(),
            )
        ]

    return ClassificationResult(classifications=items)


class StubAIClient(AIClient):
    """Heuristic classifier. ``provider='local'`` marks Phase 14 sensitive-domain runs."""

    def __init__(
        self,
        *,
        provider: str = "stub",
        model: str = "heuristic-v1",
    ) -> None:
        self.provider = provider
        self.model = model

    async def complete_json(self, request: JsonCompletionRequest) -> JsonCompletion:
        if request.schema_name == "text_completion":
            answer = (
                "I don't have enough captured browsing to answer that yet. "
                "Highlight or copy a passage and ask again."
            )
            return JsonCompletion(
                text=json.dumps({"text": answer}),
                provider=self.provider,
                model=self.model,
            )

        if request.schema_name == "claim_comparison" or request.context.get("kind") == "claim_comparison":
            from app.services.contradiction_compare import ComparisonInput, compare_locally

            comparison = compare_locally(
                ComparisonInput(
                    topic=str(request.context.get("topic", "")),
                    claim_a=str(request.context.get("claimA", "")),
                    claim_b=str(request.context.get("claimB", "")),
                    source_a_url=str(request.context.get("sourceAUrl", "")),
                    source_b_url=str(request.context.get("sourceBUrl", "")),
                )
            )
            return JsonCompletion(
                text=comparison.model_dump_json(),
                provider=self.provider,
                model=self.model,
            )

        result = classify_locally(request.context)
        return JsonCompletion(
            text=result.model_dump_json(),
            provider=self.provider,
            model=self.model,
        )

    async def complete_text(self, request: TextCompletionRequest) -> JsonCompletion:
        if "Captured material:" in request.user:
            return JsonCompletion(
                text=_stub_brief(request.user),
                provider=self.provider,
                model=self.model,
            )
        if "Captured sources:" in request.user:
            return JsonCompletion(
                text=_stub_ask_answer(request.user),
                provider=self.provider,
                model=self.model,
            )
        return JsonCompletion(
            text=(
                "I don't have enough captured browsing to answer that yet. "
                "Highlight or copy a passage and ask again."
            ),
            provider=self.provider,
            model=self.model,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hashed_embedding(text, dimensions=1536) for text in texts]


def _stub_ask_answer(user: str) -> str:
    if "[1]" in user:
        return (
            "Based on captured sources [1], here is what is on file. "
            "I am not adding anything that was not captured."
        )
    return (
        "I don't have enough captured browsing to answer that yet. "
        "Highlight or copy a passage and ask again."
    )


def _stub_brief(user: str) -> str:
    """Structured markdown so Generate brief is a document, not an Ask one-liner."""
    topic = "Untitled"
    for line in user.splitlines():
        if line.startswith("Topic:"):
            topic = line.split(":", 1)[1].strip() or topic
            break
    sources: list[str] = []
    for raw in user.split("[")[1:]:
        body = raw.split("]", 1)[-1].strip()
        if body and not body.startswith("(no related"):
            first = body.split("\n", 1)[0].strip(" -")
            if first:
                sources.append(first[:220])
    if "(no related captures)" in user or not sources:
        return (
            f"# {topic}\n\n"
            "## What's been read\n\n"
            "Nothing related is on file yet.\n\n"
            "## What's been cited\n\n"
            "No citations matched this topic.\n\n"
            "## Where sources disagree\n\n"
            "Not enough captured material to compare claims.\n\n"
            "## What still looks thin\n\n"
            "You have 0 sources; this kind of question often needs more. "
            "Highlight, copy, or linger on a passage, then generate again."
        )
    bullets = "\n".join(f"- {item}" for item in sources[:8])
    return (
        f"# {topic}\n\n"
        f"## What's been read\n\n{bullets}\n\n"
        "## What's been cited\n\n"
        "Only the captures listed above were used. Nothing was invented.\n\n"
        "## Where sources disagree\n\n"
        "The offline compiler does not pick a winner; it only lists what was captured.\n\n"
        f"## What still looks thin\n\n"
        f"You have {len(sources)} source(s). More highlights on this topic will fill the gaps."
    )


def _hashed_embedding(text: str, *, dimensions: int) -> list[float]:
    """Deterministic unit-ish vector so offline tests can still rank similar text."""
    digest = hashlib.sha256(text.casefold().encode("utf-8")).digest()
    values: list[float] = []
    seed = digest
    while len(values) < dimensions:
        seed = hashlib.sha256(seed).digest()
        for byte in seed:
            values.append((byte / 127.5) - 1.0)
            if len(values) >= dimensions:
                break
    norm = sum(v * v for v in values) ** 0.5 or 1.0
    return [v / norm for v in values[:dimensions]]
