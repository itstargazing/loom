"""One call that backs the dashboard overview.

The recent-activity feed spans eight tables with different columns, so each is
projected onto a common shape and combined with UNION ALL. That keeps the whole
overview to four queries instead of one per store, and lets Postgres do the
interleaving and limiting rather than the application.

Statement construction is kept in ``build_*`` helpers so the generated SQL can be
compiled and inspected without a database.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, Text, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.capture_event import CaptureEvent
from app.models.event_classification import EventClassification
from app.models.form_filler import FormDocument
from app.models.auto_attach import RecentDocument
from app.models.live_doc_diff import WatchedSet
from app.models.skill_stores import Contradiction
from app.routers.skills import SKILL_RESOURCES
from app.schemas.overview import (
    ActivityItem,
    CaptureSummary,
    ClassificationSummary,
    DashboardOverview,
)
from app.schemas.skills import SkillCount

router = APIRouter(prefix="/api", tags=["overview"])

#  Long passages and clauses are trimmed for the feed; the skill pages show them
#  in full.
FEED_TEXT_LIMIT = 240

RECENT_WINDOW = timedelta(hours=24)


def build_counts_query(user_id: str) -> Select[Any]:
    """Count every store in a single round trip, one scalar subquery each."""
    columns = [
        select(func.count())
        .select_from(resource.model)
        .where(resource.model.user_id == user_id)
        .scalar_subquery()
        .label(resource.slug.replace("-", "_"))
        for resource in SKILL_RESOURCES
    ]
    return select(*columns)


def build_activity_parts(user_id: str) -> list[Select[Any]]:
    """Project each store onto the shared ``ActivityItem`` column list."""
    return [
        select(
            #  Casting matters here: an untyped bind parameter inside UNION ALL
            #  leaves Postgres unable to determine the column's type.
            cast(literal(resource.slug), Text).label("skill"),
            cast(literal(resource.label), Text).label("label"),
            func.left(cast(resource.title, Text), FEED_TEXT_LIMIT).label("title"),
            func.left(cast(resource.detail, Text), FEED_TEXT_LIMIT).label("detail"),
            resource.model.source_url.label("source_url"),
            resource.model.page_title.label("page_title"),
            resource.model.confidence.label("confidence"),
            resource.model.times_seen.label("times_seen"),
            resource.model.last_seen_at.label("last_seen_at"),
        ).where(resource.model.user_id == user_id)
        for resource in SKILL_RESOURCES
    ]


def build_activity_query(user_id: str, limit: int) -> Select[Any]:
    combined = union_all(*build_activity_parts(user_id)).subquery()
    return select(combined).order_by(combined.c.last_seen_at.desc()).limit(limit)


def build_capture_query(user_id: str, now: datetime | None = None) -> Select[Any]:
    since = (now or datetime.now(UTC)) - RECENT_WINDOW
    return select(
        func.count(CaptureEvent.id).label("total_events"),
        func.count(CaptureEvent.id)
        .filter(CaptureEvent.occurred_at >= since)
        .label("events_last_day"),
        func.max(CaptureEvent.occurred_at).label("last_event_at"),
    ).where(CaptureEvent.user_id == user_id)


def build_classification_query(user_id: str) -> Select[Any]:
    return select(
        func.count(EventClassification.id)
        .filter(EventClassification.status == "succeeded")
        .label("succeeded"),
        func.count(EventClassification.id)
        .filter(EventClassification.status == "failed")
        .label("failed"),
        #  Succeeded but not yet written into the skill stores, which is the
        #  signal that routing is lagging behind classification.
        func.count(EventClassification.id)
        .filter(
            EventClassification.status == "succeeded",
            EventClassification.routed_at.is_(None),
        )
        .label("awaiting_routing"),
    ).where(EventClassification.user_id == user_id)


@router.get(
    "/overview",
    response_model=DashboardOverview,
    summary="Counts, recent activity, and pipeline health",
)
async def dashboard_overview(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    activity_limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DashboardOverview:
    counts = (await db.execute(build_counts_query(user_id))).one()
    active_contradictions = (
        await db.execute(
            select(func.count())
            .select_from(Contradiction)
            .where(
                Contradiction.user_id == user_id,
                Contradiction.dismissed.is_(False),
            )
        )
    ).scalar_one()
    skills = []
    for resource, count in zip(SKILL_RESOURCES, counts, strict=True):
        if resource.slug == "contradiction-claims":
            #  Overview tile links to the flagged-pairs page, not the raw claims list.
            skills.append(
                SkillCount(
                    skill="contradictions",
                    label="Contradictions",
                    count=int(active_contradictions),
                )
            )
        else:
            skills.append(
                SkillCount(skill=resource.slug, label=resource.label, count=count)
            )

    form_count = (
        await db.execute(
            select(func.count())
            .select_from(FormDocument)
            .where(FormDocument.user_id == user_id)
        )
    ).scalar_one()
    skills.append(
        SkillCount(skill="form-filler", label="Form Filler", count=int(form_count))
    )

    set_count = (
        await db.execute(
            select(func.count())
            .select_from(WatchedSet)
            .where(WatchedSet.user_id == user_id)
        )
    ).scalar_one()
    skills.append(
        SkillCount(
            skill="live-doc-diff",
            label="Live Doc Diff",
            count=int(set_count),
        )
    )

    recent_doc_count = (
        await db.execute(
            select(func.count())
            .select_from(RecentDocument)
            .where(RecentDocument.user_id == user_id)
        )
    ).scalar_one()
    skills.append(
        SkillCount(
            skill="auto-attach",
            label="Auto-Attach",
            count=int(recent_doc_count),
        )
    )

    activity_rows = await db.execute(build_activity_query(user_id, activity_limit))
    recent_activity = [
        ActivityItem.model_validate(dict(row._mapping)) for row in activity_rows
    ]

    capture_row = (await db.execute(build_capture_query(user_id))).one()
    classification_row = (await db.execute(build_classification_query(user_id))).one()

    return DashboardOverview(
        skills=skills,
        recent_activity=recent_activity,
        capture=CaptureSummary.model_validate(dict(capture_row._mapping)),
        classification=ClassificationSummary.model_validate(
            dict(classification_row._mapping)
        ),
    )
