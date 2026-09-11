"""Compare stub vs cloud classification on a fixed fixture set.

Usage (from backend/):
  AI_PROVIDER=stub python -m scripts.compare_providers
  AI_PROVIDER=claude ANTHROPIC_API_KEY=... python -m scripts.compare_providers --provider claude

Does not write to the database. Keep this fixture set when changing prompts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass

from app.ai.factory import reset_ai_clients
from app.ai import get_ai_client
from app.core.config import settings
from app.services.classification import ClassifiableEvent, classify_event


@dataclass(frozen=True)
class Fixture:
    name: str
    event_type: str
    source_url: str
    page_title: str
    payload: dict
    expect_any: tuple[str, ...]


FIXTURES: tuple[Fixture, ...] = (
    Fixture(
        name="deadline_highlight",
        event_type="highlight_selected",
        source_url="https://courses.example.edu/cs101/syllabus",
        page_title="CS 101 Syllabus",
        payload={
            "text": "Final paper due December 12, 2026",
            "context": "All work is due by the stated date. Final paper due December 12, 2026 at 11:59pm.",
        },
        expect_any=("deadline",),
    ),
    Fixture(
        name="glossary_term",
        event_type="highlight_selected",
        source_url="https://arxiv.org/abs/1706.03762",
        page_title="Attention Is All You Need",
        payload={
            "text": "positional encoding",
            "context": "We inject positional encoding to give the model information about token order.",
        },
        expect_any=("glossary_term", "citation", "reading_highlight"),
    ),
    Fixture(
        name="citation_copy",
        event_type="text_copied",
        source_url="https://arxiv.org/abs/1706.03762",
        page_title="Attention Is All You Need",
        payload={
            "text": (
                "The dominant sequence transduction models are based on complex "
                "recurrent or convolutional neural networks."
            ),
            "context": "According to Vaswani et al., attention mechanisms outperform recurrence.",
        },
        expect_any=("citation",),
    ),
    Fixture(
        name="contradiction_claim",
        event_type="highlight_selected",
        source_url="https://news.example.com/study",
        page_title="Study claims",
        payload={
            "text": "Coffee consumption reduces heart disease risk by 40%.",
            "context": "A new meta-analysis reports that coffee consumption reduces heart disease risk by 40%.",
        },
        expect_any=("contradiction_candidate", "reading_highlight", "citation"),
    ),
)


async def run_one(fixture: Fixture) -> dict:
    event = ClassifiableEvent(
        event_type=fixture.event_type,
        source_url=fixture.source_url,
        page_title=fixture.page_title,
        occurred_at="2026-09-09T12:00:00+00:00",
        payload=fixture.payload,
    )
    client = get_ai_client()
    outcome = await classify_event(event, client)
    categories = list(outcome.result.categories) if outcome.result else []
    hit = any(cat in categories for cat in fixture.expect_any)
    return {
        "name": fixture.name,
        "provider": outcome.provider,
        "model": outcome.model,
        "ok": outcome.succeeded,
        "categories": categories,
        "expect_any": list(fixture.expect_any),
        "matched_expectation": hit,
        "error": outcome.error,
    }


async def main_async(provider: str | None) -> int:
    if provider:
        settings.ai_provider = provider
        await reset_ai_clients()

    rows = [await run_one(fixture) for fixture in FIXTURES]
    matched = sum(1 for row in rows if row["matched_expectation"])
    print(json.dumps({"matched": matched, "total": len(rows), "rows": rows}, indent=2))
    return 0 if matched == len(rows) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=("stub", "claude", "openai"),
        default=None,
        help="Override AI_PROVIDER for this run",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args.provider)))


if __name__ == "__main__":
    main()
