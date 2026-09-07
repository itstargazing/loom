"""Persistence for queued capture events."""

from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture_event import CaptureEvent
from app.schemas.capture import CaptureEventIn


def _to_row(user_id: str, event: CaptureEventIn) -> dict[str, Any]:
    return {
        "id": event.id,
        "user_id": user_id,
        "event_type": event.type,
        "source_url": event.source_url,
        "page_title": event.page_title,
        "payload": event.payload,
        "occurred_at": event.timestamp,
        "referring_url": event.referring_url
        or (
            event.payload.get("referringUrl")
            if isinstance(event.payload.get("referringUrl"), str)
            else None
        ),
    }


async def persist_capture_events(
    session: AsyncSession,
    entries: list[tuple[str, CaptureEventIn]],
) -> list[tuple[str, UUID]]:
    """Insert raw events, skipping any already stored.

    Returns the ``(user_id, event_id)`` pairs that were newly inserted. Delivery
    is at-least-once, so conflicts on the client-generated id are expected;
    returning only new rows keeps redeliveries from triggering a second
    (billable) classification of the same event.
    """
    if not entries:
        return []

    rows = [_to_row(user_id, event) for user_id, event in entries]

    statement = (
        insert(CaptureEvent)
        .values(rows)
        .on_conflict_do_nothing(index_elements=[CaptureEvent.id])
        .returning(CaptureEvent.id)
    )
    result = await session.execute(statement)
    inserted_ids = set(result.scalars().all())
    await session.commit()

    owner_by_id = {event.id: user_id for user_id, event in entries}
    return [(owner_by_id[event_id], event_id) for event_id in inserted_ids]
