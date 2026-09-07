from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.schemas.ask import AskAnswerOut, AskQuestionIn
from app.services.ask import answer_question

router = APIRouter(prefix="/api/ask", tags=["ask"])


@router.post("", response_model=AskAnswerOut, summary="Ask Your Browsing")
async def ask(
    payload: AskQuestionIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AskAnswerOut:
    result = await answer_question(db, user_id, payload.question)
    return AskAnswerOut.model_validate(result)
