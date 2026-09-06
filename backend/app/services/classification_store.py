"""Records classification outcomes against their originating capture event."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture_event import CaptureEvent
from app.models.event_classification import EventClassification
from app.services.classification import ClassifiableEvent, ClassificationOutcome


async def load_classifiable_event(
    session: AsyncSession, capture_event_id: UUID
) -> tuple[str, ClassifiableEvent] | None:
    """Fetch a stored event in the shape the classifier expects."""
    event = await session.get(CaptureEvent, capture_event_id)
    if event is None:
        return None

    return event.user_id, ClassifiableEvent(
        event_type=event.event_type,
        source_url=event.source_url,
        page_title=event.page_title,
        occurred_at=event.occurred_at.isoformat(),
        payload=event.payload,
    )


async def record_outcome(
    session: AsyncSession,
    *,
    capture_event_id: UUID,
    user_id: str,
    outcome: ClassificationOutcome,
) -> None:
    """Upsert the outcome, so reprocessing an event replaces its previous row."""
    values = {
        "id": uuid4(),
        "capture_event_id": capture_event_id,
        "user_id": user_id,
        "status": "succeeded" if outcome.succeeded else "failed",
        "provider": outcome.provider,
        "model": outcome.model,
        "categories": outcome.result.categories if outcome.result else [],
        "result": outcome.result.model_dump() if outcome.result else None,
        "error": outcome.error,
        #  Only kept when validation failed, to iterate on the prompt.
        "raw_output": None if outcome.succeeded else outcome.raw_text,
        "attempts": outcome.attempts,
        "latency_ms": outcome.latency_ms,
    }

    statement = (
        insert(EventClassification)
        .values(values)
        .on_conflict_do_update(
            index_elements=[EventClassification.capture_event_id],
            set_={
                key: values[key]
                for key in (
                    "status",
                    "provider",
                    "model",
                    "categories",
                    "result",
                    "error",
                    "raw_output",
                    "attempts",
                    "latency_ms",
                )
            },
        )
    )

    await session.execute(statement)
    await session.commit()


async def already_handled(session: AsyncSession, capture_event_id: UUID) -> bool:
    """True when this event was already classified *and* routed.

    Routing is checked too, so an event that was classified but crashed before
    reaching the skill stores gets picked up again rather than being skipped.
    """
    result = await session.execute(
        select(EventClassification.id).where(
            EventClassification.capture_event_id == capture_event_id,
            EventClassification.status == "succeeded",
            EventClassification.routed_at.is_not(None),
        )
    )
    return result.first() is not None


async def mark_routed(session: AsyncSession, capture_event_id: UUID) -> None:
    await session.execute(
        update(EventClassification)
        .where(EventClassification.capture_event_id == capture_event_id)
        .values(routed_at=datetime.now(UTC))
    )
    await session.commit()
