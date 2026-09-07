"""Ask Your Browsing: retrieve similar captures and answer with citations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import TextCompletionRequest, get_ai_client
from app.models.capture_event import CaptureEvent
from app.services.embeddings import similar_captures
from app.services.rate_limit import limit_llm


SYSTEM = """\
You answer questions using only the captured browsing snippets provided.
If the snippets are empty or irrelevant, say you don't have enough captured \
browsing yet and do not invent sources.
Every factual sentence must point at a source by its [n] index.
Never claim something the snippets do not support.\
"""


async def answer_question(session: AsyncSession, user_id: str, question: str) -> dict:
    question = question.strip()
    matches = await similar_captures(session, user_id=user_id, query=question, limit=8)
    if not matches:
        return {
            "question": question,
            "answer": (
                "Nothing relevant is captured yet. Highlight, copy, or linger on "
                "a passage, then ask again."
            ),
            "empty": True,
            "citations": [],
        }

    event_ids = [row.capture_event_id for row, _score in matches]
    events = {
        event.id: event
        for event in (
            await session.execute(select(CaptureEvent).where(CaptureEvent.id.in_(event_ids)))
        ).scalars()
    }

    citations = []
    numbered = []
    for index, (row, score) in enumerate(matches, start=1):
        event = events.get(row.capture_event_id)
        citations.append(
            {
                "capture_event_id": str(row.capture_event_id),
                "source_url": event.source_url if event else "",
                "page_title": event.page_title if event else "",
                "snippet": row.snippet,
                "occurred_at": event.occurred_at if event else None,
                "score": round(score, 4),
            }
        )
        numbered.append(
            f"[{index}] {event.page_title if event else ''} ({event.source_url if event else ''})\n"
            f"{row.snippet}"
        )

    prompt = (
        f"Question: {question}\n\nCaptured sources:\n\n"
        + "\n\n".join(numbered)
        + "\n\nAnswer the question. Cite sources as [1], [2], …"
    )
    limit_llm(user_id)
    completion = await get_ai_client().complete_text(
        TextCompletionRequest(system=SYSTEM, user=prompt, max_output_tokens=800)
    )
    answer = completion.text.strip()
    empty = "don't have enough" in answer.casefold() or "do not have enough" in answer.casefold()
    return {
        "question": question,
        "answer": answer,
        "empty": empty,
        "citations": citations,
    }
