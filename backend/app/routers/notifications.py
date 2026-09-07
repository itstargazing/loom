from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.breakthrough import DashboardNotification
from app.schemas.notifications import NotificationListOut, NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _out(row: DashboardNotification) -> NotificationOut:
    return NotificationOut(
        id=str(row.id),
        kind=row.kind,
        title=row.title,
        body=row.body,
        href=row.href,
        read_at=row.read_at,
        dismissed_at=row.dismissed_at,
        created_at=row.created_at,
    )


@router.get("", response_model=NotificationListOut)
async def list_notifications(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationListOut:
    result = await db.execute(
        select(DashboardNotification)
        .where(
            DashboardNotification.user_id == user_id,
            DashboardNotification.dismissed_at.is_(None),
        )
        .order_by(DashboardNotification.created_at.desc())
        .limit(50)
    )
    items = [_out(row) for row in result.scalars()]
    unread = sum(1 for item in items if item.read_at is None)
    return NotificationListOut(items=items, unread=unread)


@router.post("/{notification_id}/dismiss", response_model=NotificationOut)
async def dismiss_notification(
    notification_id: UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationOut:
    row = await db.get(DashboardNotification, notification_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    row.dismissed_at = datetime.now(UTC)
    row.read_at = row.read_at or datetime.now(UTC)
    await db.commit()
    await db.refresh(row)
    return _out(row)
