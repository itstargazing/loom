from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.schemas.trail import TrailOut
from app.services.trail import load_trail

router = APIRouter(prefix="/api/trail", tags=["trail"])


@router.get("", response_model=TrailOut, summary="Research trail graph")
async def get_trail(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 80,
) -> TrailOut:
    return TrailOut.model_validate(await load_trail(db, user_id, limit=limit))
