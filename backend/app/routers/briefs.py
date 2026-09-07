from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.breakthrough import ResearchBrief
from app.schemas.briefs import BriefOut, BriefRequestIn
from app.services.briefs import generate_brief

router = APIRouter(prefix="/api/briefs", tags=["briefs"])


def _out(brief: ResearchBrief) -> BriefOut:
    return BriefOut(
        id=str(brief.id),
        topic=brief.topic,
        markdown=brief.markdown,
        source_event_ids=brief.source_event_ids,
        deadline_id=str(brief.deadline_id) if brief.deadline_id else None,
        created_at=brief.created_at,
    )


@router.post("", response_model=BriefOut, summary="Generate a research brief")
@router.post("/", response_model=BriefOut, include_in_schema=False)
async def create_brief(
    payload: BriefRequestIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BriefOut:
    try:
        brief = await generate_brief(
            db, user_id=user_id, topic=payload.topic, deadline_id=payload.deadline_id
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deadline not found")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return _out(brief)


@router.get("", response_model=list[BriefOut], summary="Recent briefs")
async def list_briefs(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BriefOut]:
    result = await db.execute(
        select(ResearchBrief)
        .where(ResearchBrief.user_id == user_id)
        .order_by(ResearchBrief.created_at.desc())
        .limit(20)
    )
    return [_out(row) for row in result.scalars()]
