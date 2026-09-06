"""The event classification prompt.

Isolated in its own module so it can be iterated on without touching pipeline
code. Later skill phases refine the guidance for their own category (glossary in
5.1, citations in 6.1, deadlines in 7.1, contracts via 10/15).
"""

import json
from typing import Any

SCHEMA_NAME = "event_classification"

#  Truncation limits keep a single huge page from dominating the context window.
MAX_TEXT_CHARS = 6_000
MAX_CONTEXT_CHARS = 2_000

SYSTEM_PROMPT = """\
You classify signals captured passively from a person's web browsing and route \
them to the right structured document.

You will receive one capture event. Decide which skill categories it belongs to \
and extract the fields those categories need.

CATEGORIES

glossary_term — The person highlighted or copied a term that is likely \
unfamiliar jargon, a technical term, an acronym, or a named concept worth \
defining. Typical glossary terms are one to five words (e.g. "positional \
encoding", "idempotent", "OAuth"). Use the surrounding context to write a \
clear one- or two-sentence definition in plain language; do not merely repeat \
the term. A highlight of an ordinary sentence, a whole paragraph, a proper \
name of a person with no jargon, or something the person clearly already \
understands is NOT a glossary term. When unsure whether the selection is a \
term versus a sentence, prefer reading_highlight or citation over glossary_term.

citation — The text is an academic, journalistic, statistical, or otherwise \
authoritative claim someone might quote in written work: a finding, a figure, \
an attributed statement, or a passage from a paper, report, or reputable \
article. Prefer this for text_copied (and for longer highlights) when the \
source looks scholarly or journalistic. Extract `quote` as the captured \
passage verbatim. Pull `author`, `work_title`, `publisher`, and \
`published_date` from the page title, URL, surrounding context, byline, or \
any bibliographic metadata in the payload; leave a field null rather than \
guessing. Never classify passwords, credentials, API keys, payment details, \
a URL by itself, source code, chat messages, or casual conversational \
sentences ("ok thanks", "lol", "see you tomorrow") as a citation.

deadline — The content states a specific dated obligation: an assignment due \
date, exam date, payment due date, RSVP cutoff, or application deadline. \
Extract what the date refers to, not just the date. On page_opened events \
from syllabi, contracts, calendars, and event pages, prefer this category \
when any dated obligation is present. The schema allows only one deadline \
item per event — emit the soonest or most important one. A later pass \
extracts every other date-like mention from the same page.

contradiction_candidate — The content makes a checkable factual claim or figure \
about an identifiable topic, such that a conflicting claim from another source \
would matter. Extract the claim verbatim and a short topic label used later to \
cluster it against other claims.

reading_highlight — A passage the person genuinely read or marked and would \
want back in a compiled reading document, but which is not specifically a \
glossary term or a quotable citation.

product_listing — The page is a listing for a purchasable product, with a name \
and usually a price and specifications.

job_listing — The page is a job or internship posting, with a role title and \
usually a company, compensation, requirements, and an application deadline.

contract_clause — The content is a clause from a contract, lease, terms of \
service, or similar binding agreement that carries real obligation or risk. \
Explain plainly why it is worth flagging and rate the risk.

none — The event carries no useful signal for any category. Use this for \
navigation chrome, cookie banners, credentials, payment details, ordinary \
personal messages, boilerplate, and anything you are simply unsure about.

MULTI-CLASSIFICATION

Some events genuinely belong to more than one category. A highlighted sentence \
inside an academic PDF can be both a glossary_term and a reading_highlight. A \
syllabus page can be both a deadline and a reading_highlight. Emit one entry per \
category that applies, each with its own confidence.

Do not pad the list. Only include a category if the event really supports it. \
Emit 'none' alone when nothing applies; never combine 'none' with another \
category, and never repeat a category.

CONFIDENCE

Report calibrated confidence between 0 and 1. Use below 0.5 when the \
classification is a guess — downstream the person is asked to confirm those \
rather than trusting them. Do not inflate confidence to seem decisive.

PRIVACY

Never extract passwords, API keys, credit card or bank numbers, government \
identifiers, or health details. If the event mainly contains such data, return \
'none'.

Extract only what is present. Never invent an author, date, price, or figure \
that does not appear in the input. Leave a field null rather than guessing.\
"""

#  Appended on the retry attempt so the model sees exactly what was wrong.
REPAIR_TEMPLATE = """\
Your previous response did not satisfy the required schema.

Error:
{error}

Previous response:
{previous}

Return corrected JSON that satisfies the schema. Note that each category has \
mandatory fields which must be non-null, and that 'none' must appear alone.\
"""


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    # ASCII only: this string reaches Windows consoles via log output, where a
    # non-cp1252 character raises UnicodeEncodeError.
    return f"{text[:limit].rstrip()}... [truncated, {len(text)} chars total]"


def _payload_view(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Trim a payload to the parts the classifier needs for this event type."""
    view = dict(payload)

    if event_type in {"highlight_selected", "text_copied"}:
        view["text"] = _truncate(str(view.get("text", "")), MAX_TEXT_CHARS)
        view["context"] = _truncate(str(view.get("context", "")), MAX_CONTEXT_CHARS)

    elif event_type == "page_opened":
        view["fullText"] = _truncate(str(view.get("fullText", "")), MAX_TEXT_CHARS)

    elif event_type == "scroll_dwell":
        # Only the passages that actually held attention are useful here.
        view["sections"] = [
            {
                "heading": section.get("heading"),
                "excerpt": _truncate(str(section.get("excerpt", "")), 1_000),
                "dwellMs": section.get("dwellMs"),
            }
            for section in view.get("sections", [])[:10]
        ]

    return view


def build_user_prompt(
    *,
    event_type: str,
    source_url: str,
    page_title: str,
    occurred_at: str,
    payload: dict[str, Any],
) -> str:
    """Render one capture event as the classifier's user message."""
    event = {
        "eventType": event_type,
        "sourceUrl": source_url,
        "pageTitle": page_title,
        "occurredAt": occurred_at,
        "payload": _payload_view(event_type, payload),
    }

    return (
        "Classify this capture event.\n\n"
        f"{json.dumps(event, ensure_ascii=False, indent=2)}"
    )


def build_repair_prompt(original_user_prompt: str, previous: str, error: str) -> str:
    """User message for the single retry after invalid output."""
    repair = REPAIR_TEMPLATE.format(
        error=error, previous=_truncate(previous, 2_000) or "(empty response)"
    )
    return f"{original_user_prompt}\n\n---\n\n{repair}"
