"""Persist and search capture embeddings (cosine in-process; pgvector optional)."""

from __future__ import annotations

import logging
import math
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import get_embedding_client
from app.models.breakthrough import CaptureEmbedding
from app.models.capture_event import CaptureEvent
from app.models.event_classification import EventClassification
from app.services.capture_text import capture_snippet, normalize_snippet

logger = logging.getLogger(__name__)

STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "have",
    "what",
    "did",
    "does",
    "about",
    "your",
    "you",
    "i",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "is",
    "it",
    "or",
    "my",
}


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_l = math.sqrt(sum(a * a for a in left))
    norm_r = math.sqrt(sum(b * b for b in right))
    if norm_l == 0 or norm_r == 0:
        return 0.0
    return dot / (norm_l * norm_r)


async def upsert_embedding(
    session: AsyncSession,
    *,
    capture_event_id: UUID,
    user_id: str,
    snippet: str,
) -> None:
    if not snippet.strip():
        return
    client = get_embedding_client()
    try:
        vectors = await client.embed([snippet[:8000]])
    except Exception:
        logger.exception("Embedding failed for %s", capture_event_id)
        return
    if not vectors:
        return
    values = {
        "capture_event_id": capture_event_id,
        "user_id": user_id,
        "embedding": vectors[0],
        "model": client.model,
        "snippet": snippet[:4000],
    }
    await session.execute(
        insert(CaptureEmbedding)
        .values(values)
        .on_conflict_do_update(
            index_elements=[CaptureEmbedding.capture_event_id],
            set_={
                "embedding": values["embedding"],
                "model": values["model"],
                "snippet": values["snippet"],
            },
        )
    )
    await session.commit()


def lexical_score(query: str, *texts: str) -> float:
    """Token overlap. Stub hashed embeddings are not semantic; this still finds keywords."""
    tokens = {
        token
        for token in normalize_snippet(query).split()
        if len(token) > 2 and token not in STOPWORDS
    }
    if not tokens:
        return 0.0
    haystack = set(normalize_snippet(" ".join(part for part in texts if part)).split())
    if not haystack:
        return 0.0
    return len(tokens & haystack) / len(tokens)


async def similar_captures(
    session: AsyncSession,
    *,
    user_id: str,
    query: str,
    limit: int = 8,
    min_score: float = 0.15,
) -> list[tuple[CaptureEmbedding, float]]:
    client = get_embedding_client()
    vectors = await client.embed([query[:8000]])
    query_vec = vectors[0]
    result = await session.execute(
        select(CaptureEmbedding).where(CaptureEmbedding.user_id == user_id)
    )
    by_id: dict[UUID, CaptureEmbedding] = {}
    best: dict[UUID, tuple[CaptureEmbedding, float]] = {}
    for row in result.scalars():
        by_id[row.capture_event_id] = row
        score = cosine_similarity(query_vec, list(row.embedding or []))
        if score >= min_score:
            best[row.capture_event_id] = (row, score)

    # Hashed stub vectors barely correlate similar phrasing. Keyword overlap
    # still answers "what did I save about X" from classification snippets.
    classified = await session.execute(
        select(EventClassification, CaptureEvent)
        .join(CaptureEvent, CaptureEvent.id == EventClassification.capture_event_id)
        .where(EventClassification.user_id == user_id)
        .order_by(EventClassification.created_at.desc())
        .limit(400)
    )
    for classification, event in classified.all():
        snippet = classification.snippet or capture_snippet(
            event.event_type, event.payload
        )
        score = lexical_score(query, snippet, event.page_title, event.source_url)
        if score < min_score:
            continue
        current = best.get(event.id)
        if current is not None and score <= current[1]:
            continue
        row = by_id.get(event.id)
        if row is None:
            row = CaptureEmbedding(
                capture_event_id=event.id,
                user_id=user_id,
                embedding=[],
                snippet=snippet[:4000],
                model="lexical",
            )
        best[event.id] = (row, score)

    ranked = sorted(best.values(), key=lambda item: item[1], reverse=True)
    return ranked[:limit]
