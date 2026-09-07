"""Research trail: ordered graph from timestamps and referring URLs."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture_event import CaptureEvent
from app.models.event_classification import EventClassification

PROXIMITY = timedelta(minutes=20)


async def load_trail(session: AsyncSession, user_id: str, limit: int = 80) -> dict:
    result = await session.execute(
        select(CaptureEvent, EventClassification)
        .outerjoin(
            EventClassification,
            EventClassification.capture_event_id == CaptureEvent.id,
        )
        .where(CaptureEvent.user_id == user_id)
        .order_by(CaptureEvent.occurred_at.desc())
        .limit(limit)
    )
    # Newest window, then chronological so the trail reads left-to-right.
    rows = list(reversed(result.all()))
    nodes = []
    by_url: dict[str, str] = {}
    previous_id: str | None = None
    previous_at = None
    edges: list[dict[str, str]] = []

    for event, classification in rows:
        node_id = str(event.id)
        nodes.append(
            {
                "id": node_id,
                "capture_event_id": node_id,
                "snippet": (classification.snippet if classification else "")[:400],
                "source_url": event.source_url,
                "page_title": event.page_title,
                "referring_url": event.referring_url,
                "occurred_at": event.occurred_at,
                "categories": classification.categories if classification else [],
                "review_status": classification.review_status if classification else None,
            }
        )
        if event.referring_url and event.referring_url in by_url:
            edges.append(
                {"source": by_url[event.referring_url], "target": node_id, "kind": "referrer"}
            )
        elif (
            previous_id
            and previous_at is not None
            and event.occurred_at - previous_at <= PROXIMITY
        ):
            edges.append({"source": previous_id, "target": node_id, "kind": "led_to"})
        by_url[event.source_url] = node_id
        previous_id = node_id
        previous_at = event.occurred_at

    return {
        "nodes": nodes,
        "edges": edges,
        "session_started_at": nodes[0]["occurred_at"] if nodes else None,
        "extras": {},
    }
