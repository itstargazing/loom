"""Deadline nudges: thin related reading → in-dashboard notification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breakthrough import DashboardNotification, DeadlineNudgeLog
from app.models.skill_stores import Citation, Deadline, ReadingCompilerEntry
from app.services.embeddings import similar_captures

LOOKAHEAD = timedelta(days=7)
THIN_RELATED = 3


async def scan_nudges(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    until = now + LOOKAHEAD
    result = await session.execute(
        select(Deadline).where(
            Deadline.due_date.is_not(None),
            Deadline.due_date >= now,
            Deadline.due_date <= until,
        )
    )
    written = 0
    today = now.date().isoformat()
    for deadline in result.scalars():
        exists = await session.execute(
            select(DeadlineNudgeLog.id).where(
                DeadlineNudgeLog.user_id == deadline.user_id,
                DeadlineNudgeLog.deadline_id == deadline.id,
                DeadlineNudgeLog.day == today,
            )
        )
        if exists.first():
            continue
        related = await similar_captures(
            session, user_id=deadline.user_id, query=deadline.title, limit=8, min_score=0.2
        )
        citations = (
            await session.execute(
                select(func.count()).where(
                    Citation.user_id == deadline.user_id,
                )
            )
        ).scalar_one()
        readings = (
            await session.execute(
                select(func.count()).where(ReadingCompilerEntry.user_id == deadline.user_id)
            )
        ).scalar_one()
        related_n = len(related)
        if related_n >= THIN_RELATED:
            continue
        due = deadline.due_date.date().isoformat() if deadline.due_date else "soon"
        body = (
            f"{deadline.title} is due {due}. Related captures look thin "
            f"({related_n} close snippets, {citations} citations and {readings} "
            "reading passages on file). I can generate a brief from what you have, "
            "or you can keep reading — no rush implied."
        )
        session.add(
            DashboardNotification(
                user_id=deadline.user_id,
                kind="deadline_nudge",
                title=f"Want a hand with {deadline.title}?",
                body=body,
                href="/skills/deadlines",
                payload={"deadlineId": str(deadline.id)},
            )
        )
        session.add(
            DeadlineNudgeLog(
                user_id=deadline.user_id,
                deadline_id=deadline.id,
                day=today,
            )
        )
        written += 1
    if written:
        await session.commit()
    return written
