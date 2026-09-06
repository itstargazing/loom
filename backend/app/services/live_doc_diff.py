"""Orchestrate snapshots and pairwise diffs for watched document sets."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture_event import CaptureEvent
from app.models.live_doc_diff import (
    DocumentDiffEvent,
    DocumentSnapshot,
    WatchedDocument,
    WatchedSet,
)
from app.services.doc_diff import compute_diff, content_hash


async def latest_capture_text(
    session: AsyncSession, user_id: str, source_url: str
) -> tuple[str | None, uuid.UUID | None]:
    result = await session.execute(
        select(CaptureEvent)
        .where(
            CaptureEvent.user_id == user_id,
            CaptureEvent.source_url == source_url,
            CaptureEvent.event_type == "page_opened",
        )
        .order_by(CaptureEvent.occurred_at.desc())
        .limit(1)
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None, None
    text = str((event.payload or {}).get("fullText") or "").strip()
    return (text or None), event.id


async def add_snapshot(
    session: AsyncSession,
    document: WatchedDocument,
    text: str,
    *,
    capture_event_id: uuid.UUID | None = None,
) -> DocumentSnapshot | None:
    """Store a snapshot when the text hash is new. Returns None if unchanged."""
    digest = content_hash(text)
    existing = await session.execute(
        select(DocumentSnapshot)
        .where(DocumentSnapshot.document_id == document.id)
        .order_by(DocumentSnapshot.captured_at.desc())
        .limit(1)
    )
    latest = existing.scalar_one_or_none()
    if latest is not None and latest.content_hash == digest:
        return None

    snapshot = DocumentSnapshot(
        document_id=document.id,
        user_id=document.user_id,
        content_text=text,
        content_hash=digest,
        capture_event_id=capture_event_id,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def refresh_document_from_captures(
    session: AsyncSession, document: WatchedDocument
) -> DocumentSnapshot | None:
    text, event_id = await latest_capture_text(
        session, document.user_id, document.source_url
    )
    if not text:
        return None
    return await add_snapshot(
        session, document, text, capture_event_id=event_id
    )


async def latest_snapshot(
    session: AsyncSession, document_id: uuid.UUID
) -> DocumentSnapshot | None:
    result = await session.execute(
        select(DocumentSnapshot)
        .where(DocumentSnapshot.document_id == document_id)
        .order_by(DocumentSnapshot.captured_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def scan_watched_set(
    session: AsyncSession, watched_set: WatchedSet
) -> list[DocumentDiffEvent]:
    """Refresh snapshots from captures, then compare every document pair."""
    docs = (
        await session.execute(
            select(WatchedDocument)
            .where(WatchedDocument.set_id == watched_set.id)
            .order_by(WatchedDocument.created_at.asc())
        )
    ).scalars().all()

    for document in docs:
        await refresh_document_from_captures(session, document)

    snapshots: dict[uuid.UUID, DocumentSnapshot] = {}
    for document in docs:
        snap = await latest_snapshot(session, document.id)
        if snap is not None:
            snapshots[document.id] = snap

    written: list[DocumentDiffEvent] = []
    for i, left in enumerate(docs):
        left_snap = snapshots.get(left.id)
        if left_snap is None:
            continue
        for right in docs[i + 1 :]:
            right_snap = snapshots.get(right.id)
            if right_snap is None:
                continue

            #  Skip if we already recorded this exact snapshot pair.
            exists = await session.execute(
                select(DocumentDiffEvent.id).where(
                    DocumentDiffEvent.set_id == watched_set.id,
                    DocumentDiffEvent.left_snapshot_id == left_snap.id,
                    DocumentDiffEvent.right_snapshot_id == right_snap.id,
                )
            )
            if exists.scalar_one_or_none() is not None:
                continue

            result = compute_diff(
                left.label,
                left_snap.content_text,
                right.label,
                right_snap.content_text,
            )
            if not result.unified and not result.is_meaningful:
                #  Still record formatting-only / identical so the timeline shows a scan.
                if left_snap.content_hash == right_snap.content_hash:
                    continue

            event = DocumentDiffEvent(
                set_id=watched_set.id,
                user_id=watched_set.user_id,
                left_document_id=left.id,
                right_document_id=right.id,
                left_snapshot_id=left_snap.id,
                right_snapshot_id=right_snap.id,
                unified_diff=result.unified,
                change_summary=result.summary,
                is_meaningful=result.is_meaningful,
            )
            session.add(event)
            written.append(event)

    await session.flush()
    return written


async def scan_all_users(session: AsyncSession) -> int:
    sets = (await session.execute(select(WatchedSet))).scalars().all()
    total = 0
    for watched_set in sets:
        events = await scan_watched_set(session, watched_set)
        total += len(events)
    await session.commit()
    return total


async def unread_meaningful_count(session: AsyncSession, user_id: str) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(DocumentDiffEvent)
        .where(
            DocumentDiffEvent.user_id == user_id,
            DocumentDiffEvent.is_meaningful.is_(True),
            DocumentDiffEvent.viewed_at.is_(None),
        )
    )
    return int(result.scalar_one())


async def mark_set_viewed(
    session: AsyncSession, watched_set: WatchedSet
) -> None:
    now = datetime.now(UTC)
    watched_set.last_viewed_at = now
    events = (
        await session.execute(
            select(DocumentDiffEvent).where(
                DocumentDiffEvent.set_id == watched_set.id,
                DocumentDiffEvent.viewed_at.is_(None),
            )
        )
    ).scalars().all()
    for event in events:
        event.viewed_at = now
