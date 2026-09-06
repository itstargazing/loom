"""Classify sample events and show where each result would be routed.

Needs no database or Redis, so it is the quickest way to see what the current
prompt and provider actually produce, and which store each result lands in:

    python -m scripts.demo_classify
"""

import asyncio
import json

from app.ai import get_ai_client
from app.services.classification import ClassifiableEvent, classify_event
from app.services.dedup import dedup_key
from app.services.skill_router import ROUTES, RoutingContext

SAMPLES: list[ClassifiableEvent] = [
    ClassifiableEvent(
        event_type="highlight_selected",
        source_url="https://arxiv.org/abs/1706.03762",
        page_title="Attention Is All You Need",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload={
            "text": "positional encoding",
            "context": (
                "Since our model contains no recurrence and no convolution, we "
                "add positional encodings to the input embeddings so the model "
                "can make use of the order of the sequence."
            ),
        },
    ),
    ClassifiableEvent(
        event_type="text_copied",
        source_url="https://www.nature.com/articles/s41586-024-00001",
        page_title="Global temperature trends",
        occurred_at="2026-08-28T10:05:00+00:00",
        payload={
            "text": (
                "According to Hansen et al, global average temperatures rose by "
                "1.2 degrees Celsius relative to the pre-industrial baseline."
            )
        },
    ),
    ClassifiableEvent(
        event_type="page_opened",
        source_url="https://university.edu/cs101/syllabus",
        page_title="CS101 Syllabus",
        occurred_at="2026-08-28T10:10:00+00:00",
        payload={
            "fullText": (
                "Problem Set 3 is due 2026-09-15 and must be submitted through "
                "the course portal no later than 5pm. Late work is not accepted."
            )
        },
    ),
    ClassifiableEvent(
        event_type="scroll_dwell",
        source_url="https://example.com/essay",
        page_title="On Attention",
        occurred_at="2026-08-28T10:15:00+00:00",
        payload={
            "sections": [
                {"heading": "Intro", "excerpt": "A brief opening.", "dwellMs": 1_200},
                {
                    "heading": "The core argument",
                    "excerpt": "Attention is a scarce resource, and its scarcity "
                    "is what gives it economic value.",
                    "dwellMs": 42_000,
                },
            ]
        },
    ),
    ClassifiableEvent(
        event_type="text_copied",
        source_url="https://bank.example.com/login",
        page_title="Sign in",
        occurred_at="2026-08-28T10:20:00+00:00",
        payload={"text": "my password is hunter2"},
    ),
]


async def main() -> None:
    client = get_ai_client()
    print(f"provider={client.provider} model={client.model}\n")

    for event in SAMPLES:
        outcome = await classify_event(event, client)

        print(f"-- {event.event_type} @ {event.source_url}")
        if not outcome.succeeded:
            print(f"   FAILED after {outcome.attempts} attempt(s): {outcome.error}\n")
            continue

        context = RoutingContext(
            user_id="dev-user",
            capture_event_id=None,
            source_url=event.source_url,
            page_title=event.page_title,
        )

        for item in outcome.result.classifications:
            print(f"   {item.category}  (confidence {item.confidence:.2f})")
            print(f"     reason: {item.reason}")

            fields = item.fields.present()
            if fields:
                print(f"     fields: {json.dumps(fields, ensure_ascii=False)}")

            route = ROUTES.get(item.category)
            if route is None:
                print("     routes to: (nothing)")
            else:
                key = dedup_key(*route.key(item.fields, context))
                print(f"     routes to: {route.model.__tablename__} (dedup {key[:12]})")

        print(f"   attempts={outcome.attempts} latency={outcome.latency_ms}ms\n")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
