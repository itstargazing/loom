"""On-demand research briefs from related captures."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import TextCompletionRequest, get_ai_client
from app.models.breakthrough import ResearchBrief
from app.models.capture_event import CaptureEvent
from app.models.skill_stores import Deadline
from app.services.embeddings import similar_captures
from app.services.rate_limit import limit_llm

SYSTEM = """\
Write a one-page research brief in Markdown from the captured sources.
Sections:
1. What's been read
2. What's been cited
3. Where sources disagree
4. What still looks thin (as a helpful observation, not a judgment)

If there are few sources, say so plainly ("you have 2 sources; this kind of \
question often needs more"). Do not invent readings or citations.\
"""


async def generate_brief(
    session: AsyncSession,
    *,
    user_id: str,
    topic: str | None,
    deadline_id: str | None,
) -> ResearchBrief:
    deadline = None
    if deadline_id:
        deadline = await session.get(Deadline, uuid.UUID(deadline_id))
        if deadline is None or deadline.user_id != user_id:
            raise KeyError("deadline")
        topic = topic or deadline.title
    if not topic or not topic.strip():
        raise ValueError("topic required")
    topic = topic.strip()

    matches = await similar_captures(session, user_id=user_id, query=topic, limit=12)
    event_ids = [row.capture_event_id for row, _score in matches]
    events = {
        event.id: event
        for event in (
            await session.execute(select(CaptureEvent).where(CaptureEvent.id.in_(event_ids)))
        ).scalars()
    } if event_ids else {}
    numbered = []
    for index, (row, _score) in enumerate(matches, start=1):
        event = events.get(row.capture_event_id)
        title = event.page_title if event else ""
        url = event.source_url if event else ""
        numbered.append(f"[{index}] {title} ({url})\n{row.snippet[:500]}")
    deadline_block = ""
    if deadline:
        due = deadline.due_date.date().isoformat() if deadline.due_date else deadline.due_text
        deadline_block = (
            f"\nDeadline: {deadline.title}\nDue: {due}\n"
            f"Context: {deadline.context_snippet or '(none)'}\n"
        )
    material = "\n\n".join(numbered) or "(no related captures)"
    limit_llm(user_id)
    completion = await get_ai_client().complete_text(
        TextCompletionRequest(
            system=SYSTEM,
            user=(
                f"Topic: {topic}{deadline_block}\nCaptured material:\n{material}"
            ),
            max_output_tokens=1200,
        )
    )
    brief = ResearchBrief(
        user_id=user_id,
        topic=topic,
        markdown=completion.text.strip(),
        source_event_ids=[str(row.capture_event_id) for row, _ in matches],
        deadline_id=deadline.id if deadline else None,
    )
    session.add(brief)
    await session.commit()
    await session.refresh(brief)
    return brief
