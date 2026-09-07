from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.schemas.digest import DigestActionIn, DigestOut
from app.services.digest import apply_digest_action, load_digest

router = APIRouter(prefix="/api/digest", tags=["digest"])


@router.get("", response_model=DigestOut, summary="Last 24 hours of classified captures")
async def get_digest(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DigestOut:
    payload = await load_digest(db, user_id)
    return DigestOut.model_validate(payload)


@router.post("/{classification_id}", response_model=DigestOut, summary="Accept, reassign, or discard")
async def post_digest_action(
    classification_id: UUID,
    payload: DigestActionIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DigestOut:
    try:
        await apply_digest_action(
            db,
            user_id=user_id,
            classification_id=classification_id,
            action=payload.action,
            category=payload.category,
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
    return DigestOut.model_validate(await load_digest(db, user_id))
