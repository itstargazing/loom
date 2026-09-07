"""Inspection endpoints for classification outcomes.

Phase 3.1 has no dashboard surface yet, so these exist to verify the pipeline
end to end and to iterate on the prompt against real captured events.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import get_ai_client
from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.event_classification import EventClassification
from app.schemas.classification_log import (
    CategoryCount,
    ClassificationStats,
    EventClassificationOut,
)
from app.services.classification import classify_event
from app.services.classification_store import load_classifiable_event, record_outcome
from app.services.rate_limit import limit_classification

router = APIRouter(prefix="/api/classifications", tags=["classifications"])


@router.get(
    "",
    response_model=list[EventClassificationOut],
    summary="List recent classification outcomes",
)
async def list_classifications(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    category: Annotated[str | None, Query()] = None,
    only_failed: Annotated[bool, Query()] = False,
    capture_event_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[EventClassification]:
    query = (
        select(EventClassification)
        .where(EventClassification.user_id == user_id)
        .order_by(EventClassification.created_at.desc())
        .limit(limit)
    )

    if category:
        query = query.where(EventClassification.categories.any(category))
    if only_failed:
        query = query.where(EventClassification.status == "failed")
    if capture_event_id is not None:
        query = query.where(EventClassification.capture_event_id == capture_event_id)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get(
    "/stats",
    response_model=ClassificationStats,
    summary="Aggregate classification counts",
)
async def classification_stats(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClassificationStats:
    totals = await db.execute(
        select(EventClassification.status, func.count())
        .where(EventClassification.user_id == user_id)
        .group_by(EventClassification.status)
    )
    counts = dict(totals.all())

    # unnest turns the categories array into one row per category so it can be
    # grouped, since an event may carry several.
    category_column = func.unnest(EventClassification.categories).label("category")
    per_category = await db.execute(
        select(category_column, func.count())
        .where(EventClassification.user_id == user_id)
        .group_by(category_column)
        .order_by(func.count().desc())
    )

    return ClassificationStats(
        total=sum(counts.values()),
        succeeded=counts.get("succeeded", 0),
        failed=counts.get("failed", 0),
        by_category=[
            CategoryCount(category=category, count=count)
            for category, count in per_category.all()
        ],
    )


@router.post(
    "/{capture_event_id}/reclassify",
    response_model=EventClassificationOut,
    summary="Reclassify one event now",
)
async def reclassify(
    capture_event_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventClassification:
    """Run the classifier synchronously and replace the stored outcome.

    Bypasses the queue on purpose: this is the loop used when tuning the prompt.
    """
    limit_classification(user_id)
    loaded = await load_classifiable_event(db, capture_event_id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Capture event not found"
        )

    owner_id, event = loaded
    if owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Capture event not found"
        )

    outcome = await classify_event(event, get_ai_client())
    from app.services.capture_text import capture_snippet

    await record_outcome(
        db,
        capture_event_id=capture_event_id,
        user_id=owner_id,
        outcome=outcome,
        snippet=capture_snippet(event.event_type, event.payload),
    )

    result = await db.execute(
        select(EventClassification).where(
            EventClassification.capture_event_id == capture_event_id
        )
    )
    stored = result.scalar_one()
    return stored
