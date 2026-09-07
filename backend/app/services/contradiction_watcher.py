"""Scan recent claims, cluster by topic, and promote conflicting pairs.

This is not tied to a single capture event: it runs as a background pass over
``contradiction_claims`` and writes rows into ``contradictions``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIClient
from app.core.config import settings
from app.models.skill_stores import Contradiction, ContradictionClaim
from app.services.contradiction_cluster import ClaimRef, cluster_by_topic
from app.services.contradiction_compare import ComparisonInput, compare_claims, compare_locally

logger = logging.getLogger(__name__)

#  Skip pairs the user already dismissed (by claim ids).
MIN_CONFIDENCE_TO_FLAG = 0.5


def _canonical_pair(
    left: ContradictionClaim, right: ContradictionClaim
) -> tuple[ContradictionClaim, ContradictionClaim]:
    """Stable order so (A,B) and (B,A) hit the same unique constraint."""
    if str(left.id) <= str(right.id):
        return left, right
    return right, left


def _evidence(
    side_a: ContradictionClaim,
    side_b: ContradictionClaim,
    cluster_claims: list[ContradictionClaim],
) -> tuple[int, int, list[dict]]:
    """Count-based support. Does not decide which side is true."""
    evidence: list[dict] = []
    agree_a = 0
    agree_b = 0
    for claim in cluster_claims:
        if claim.id == side_a.id:
            stance = "side_a"
            agree_a += 1
        elif claim.id == side_b.id:
            stance = "side_b"
            agree_b += 1
        else:
            vs_a = compare_locally(
                ComparisonInput(
                    topic=side_a.topic,
                    claim_a=side_a.claim,
                    claim_b=claim.claim,
                    source_a_url=side_a.source_url,
                    source_b_url=claim.source_url,
                )
            )
            vs_b = compare_locally(
                ComparisonInput(
                    topic=side_b.topic,
                    claim_a=side_b.claim,
                    claim_b=claim.claim,
                    source_a_url=side_b.source_url,
                    source_b_url=claim.source_url,
                )
            )
            if vs_a.conflicts and not vs_b.conflicts:
                stance = "side_b"
                agree_b += 1
            elif vs_b.conflicts and not vs_a.conflicts:
                stance = "side_a"
                agree_a += 1
            else:
                stance = "unaligned"
        evidence.append(
            {
                "claim": claim.claim,
                "sourceUrl": claim.source_url,
                "pageTitle": claim.page_title,
                "stance": stance,
                "excerpt": claim.claim[:280],
            }
        )
    return agree_a, agree_b, evidence


def _host(url: str) -> str:
    cleaned = url.removeprefix("https://").removeprefix("http://")
    return cleaned.split("/")[0].removeprefix("www.")


async def _dismissed_pairs(
    session: AsyncSession, user_id: str
) -> set[tuple[uuid.UUID, uuid.UUID]]:
    result = await session.execute(
        select(Contradiction.claim_a_id, Contradiction.claim_b_id).where(
            Contradiction.user_id == user_id,
            Contradiction.dismissed.is_(True),
            Contradiction.claim_a_id.is_not(None),
            Contradiction.claim_b_id.is_not(None),
        )
    )
    pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for claim_a_id, claim_b_id in result.all():
        if claim_a_id is None or claim_b_id is None:
            continue
        ordered = tuple(sorted((claim_a_id, claim_b_id)))
        pairs.add((ordered[0], ordered[1]))
    return pairs


async def load_recent_claims(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    lookback_days: int | None = None,
) -> list[ContradictionClaim]:
    since = datetime.now(UTC) - timedelta(
        days=lookback_days or settings.contradiction_lookback_days
    )
    stmt = select(ContradictionClaim).where(ContradictionClaim.last_seen_at >= since)
    if user_id is not None:
        stmt = stmt.where(ContradictionClaim.user_id == user_id)
    stmt = stmt.order_by(ContradictionClaim.last_seen_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def flag_conflicts_for_user(
    session: AsyncSession,
    client: AIClient,
    *,
    user_id: str,
    claims: list[ContradictionClaim] | None = None,
) -> int:
    """Cluster one user's claims and upsert any new conflicting pairs.

    Returns the number of newly written (or refreshed) contradiction rows.
    """
    rows = claims if claims is not None else [
        claim for claim in await load_recent_claims(session, user_id=user_id)
    ]
    if len(rows) < 2:
        return 0

    dismissed = await _dismissed_pairs(session, user_id)
    refs = [
        ClaimRef(
            id=claim.id,
            topic=claim.topic,
            claim=claim.claim,
            source_url=claim.source_url,
        )
        for claim in rows
    ]
    by_id = {claim.id: claim for claim in rows}
    written = 0

    for cluster in cluster_by_topic(refs):
        if len(cluster) < 2:
            continue
        #  Prefer a readable topic label from the densest member.
        topic_label = max((member.topic for member in cluster), key=len)
        for index, left_ref in enumerate(cluster):
            for right_ref in cluster[index + 1 :]:
                left = by_id[left_ref.id]  # type: ignore[index]
                right = by_id[right_ref.id]  # type: ignore[index]
                if _host(left.source_url) == _host(right.source_url) and left.source_url:
                    #  Same source repeating itself is not a cross-source conflict.
                    if left.source_url == right.source_url:
                        continue
                claim_a, claim_b = _canonical_pair(left, right)
                pair_key = (claim_a.id, claim_b.id)
                if pair_key in dismissed:
                    continue

                comparison = await compare_claims(
                    client,
                    ComparisonInput(
                        topic=topic_label,
                        claim_a=claim_a.claim,
                        claim_b=claim_b.claim,
                        source_a_url=claim_a.source_url,
                        source_b_url=claim_b.source_url,
                    ),
                )
                if not comparison.conflicts or comparison.confidence < MIN_CONFIDENCE_TO_FLAG:
                    continue

                cluster_rows = [by_id[member.id] for member in cluster]
                agree_a, agree_b, evidence = _evidence(claim_a, claim_b, cluster_rows)

                stmt = (
                    insert(Contradiction)
                    .values(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        topic=topic_label,
                        claim_a=claim_a.claim,
                        claim_b=claim_b.claim,
                        source_a_url=claim_a.source_url,
                        source_b_url=claim_b.source_url,
                        explanation=comparison.explanation.strip(),
                        dismissed=False,
                        claim_a_id=claim_a.id,
                        claim_b_id=claim_b.id,
                        agree_count=agree_a,
                        disagree_count=agree_b,
                        evidence=evidence,
                    )
                    .on_conflict_do_update(
                        constraint="uq_contradictions_pair",
                        set_={
                            "topic": topic_label,
                            "claim_a": claim_a.claim,
                            "claim_b": claim_b.claim,
                            "source_a_url": claim_a.source_url,
                            "source_b_url": claim_b.source_url,
                            "explanation": comparison.explanation.strip(),
                            "agree_count": agree_a,
                            "disagree_count": agree_b,
                            "evidence": evidence,
                            "dismissed": Contradiction.__table__.c.dismissed,
                        },
                    )
                )
                await session.execute(stmt)
                written += 1

    if written:
        await session.commit()
    return written


async def scan_all_users(session: AsyncSession, client: AIClient) -> int:
    """One watcher pass across every user that has recent claims."""
    claims = await load_recent_claims(session)
    by_user: dict[str, list[ContradictionClaim]] = {}
    for claim in claims:
        by_user.setdefault(claim.user_id, []).append(claim)

    total = 0
    for user_id, user_claims in by_user.items():
        total += await flag_conflicts_for_user(
            session, client, user_id=user_id, claims=user_claims
        )
    return total
