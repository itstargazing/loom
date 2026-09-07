import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.capture_event import CaptureEvent
from app.schemas.capture import CaptureBatchAck, CaptureBatchIn, CaptureEventOut
from app.services.capture_inline import persist_and_classify_inline
from app.services.capture_queue import enqueue_capture_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/capture", tags=["capture"])


@router.post(
    "/events",
    response_model=CaptureBatchAck,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a batch of capture events",
)
async def ingest_events(batch: CaptureBatchIn, user_id: CurrentUserId) -> CaptureBatchAck:
    """Accept a batch from the extension and queue it for async persistence.

    Returns as soon as the events are on the queue so the extension is never
    blocked on database writes.
    """
    if len(batch.events) > settings.max_events_per_batch:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Batch exceeds {settings.max_events_per_batch} events",
        )

    try:
        queued = await enqueue_capture_events(user_id, batch.events)
    except Exception as error:
        logger.warning(
            "Capture queue unavailable (%s); writing %s event(s) inline",
            error,
            len(batch.events),
        )
        queued = await persist_and_classify_inline(user_id, batch.events)

    return CaptureBatchAck(accepted=len(batch.events), queued=queued)


@router.get(
    "/events",
    response_model=list[CaptureEventOut],
    summary="List recently persisted capture events",
)
async def list_events(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[CaptureEvent]:
    """Read back stored events. Used to verify the pipeline and by the dashboard."""
    result = await db.execute(
        select(CaptureEvent)
        .where(CaptureEvent.user_id == user_id)
        .order_by(CaptureEvent.occurred_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
