"""Records classification outcomes against their originating capture event."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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
    snippet: str = "",
) -> str:
    """Upsert the outcome, so reprocessing an event replaces its previous row."""
    max_confidence = 0.0
    if outcome.result and outcome.result.classifications:
        max_confidence = max(item.confidence for item in outcome.result.classifications)

    review_status = "auto_routed"
    if outcome.succeeded and outcome.result is not None:
        routable = [
            item for item in outcome.result.classifications if item.category != "none"
        ]
        if routable and any(
            item.confidence < settings.classification_auto_route_min_confidence
            for item in routable
        ):
            review_status = "pending_review"

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
        "raw_output": outcome.raw_text,
        "attempts": outcome.attempts,
        "latency_ms": outcome.latency_ms,
        "cached": outcome.cached,
        "max_confidence": max_confidence,
        "snippet": snippet,
        "review_status": review_status,
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
                    "cached",
                    "max_confidence",
                    "snippet",
                    "review_status",
                )
            },
        )
    )

    await session.execute(statement)
    await session.commit()
    return review_status


async def already_handled(session: AsyncSession, capture_event_id: UUID) -> bool:
    """True when this event was already classified *and* routed.

    Routing is checked too, so an event that was classified but crashed before
    reaching the skill stores gets picked up again rather than being skipped.
    """
    result = await session.execute(
        select(EventClassification.id, EventClassification.review_status).where(
            EventClassification.capture_event_id == capture_event_id,
            EventClassification.status == "succeeded",
        )
    )
    row = result.first()
    if row is None:
        return False
    _id, review_status = row
    if review_status == "pending_review":
        return True
    routed = await session.execute(
        select(EventClassification.id).where(
            EventClassification.capture_event_id == capture_event_id,
            EventClassification.routed_at.is_not(None),
        )
    )
    return routed.first() is not None


async def mark_routed(session: AsyncSession, capture_event_id: UUID) -> None:
    await session.execute(
        update(EventClassification)
        .where(EventClassification.capture_event_id == capture_event_id)
        .values(routed_at=datetime.now(UTC))
    )
    await session.commit()
