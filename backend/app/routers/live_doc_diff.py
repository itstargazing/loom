"""Multi-Doc Live Diff API: watched sets, snapshots, and divergence events."""

from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.live_doc_diff import (
    DocumentDiffEvent,
    DocumentSnapshot,
    WatchedDocument,
    WatchedSet,
)
from app.schemas.live_doc_diff import (
    DocumentDiffEventOut,
    SnapshotIn,
    UnreadCountOut,
    WatchedDocumentIn,
    WatchedDocumentOut,
    WatchedSetDetailOut,
    WatchedSetIn,
    WatchedSetOut,
)
from app.services import live_doc_diff as service

router = APIRouter(prefix="/api", tags=["live-doc-diff"])


async def _owned_set(
    db: AsyncSession, set_id: uuid.UUID, user_id: str
) -> WatchedSet:
    result = await db.execute(
        select(WatchedSet).where(
            WatchedSet.id == set_id, WatchedSet.user_id == user_id
        )
    )
    watched = result.scalar_one_or_none()
    if watched is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Watched set not found"
        )
    return watched


async def _owned_document(
    db: AsyncSession, document_id: uuid.UUID, user_id: str
) -> WatchedDocument:
    result = await db.execute(
        select(WatchedDocument).where(
            WatchedDocument.id == document_id,
            WatchedDocument.user_id == user_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return document


def _label_from_url(url: str, fallback: str | None) -> str:
    if fallback and fallback.strip():
        return fallback.strip()[:512]
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or parsed.netloc or url
    return path.split("/")[-1][:512] or url[:512]


async def _document_out(
    db: AsyncSession, document: WatchedDocument
) -> WatchedDocumentOut:
    stats = (
        await db.execute(
            select(
                func.count(DocumentSnapshot.id),
                func.max(DocumentSnapshot.captured_at),
            ).where(DocumentSnapshot.document_id == document.id)
        )
    ).one()
    return WatchedDocumentOut(
        id=document.id,
        set_id=document.set_id,
        label=document.label,
        source_url=document.source_url,
        created_at=document.created_at,
        snapshot_count=int(stats[0] or 0),
        latest_snapshot_at=stats[1],
    )


async def _events_for_set(
    db: AsyncSession, set_id: uuid.UUID
) -> list[DocumentDiffEventOut]:
    docs = (
        await db.execute(
            select(WatchedDocument).where(WatchedDocument.set_id == set_id)
        )
    ).scalars().all()
    labels = {doc.id: doc.label for doc in docs}

    rows = (
        await db.execute(
            select(DocumentDiffEvent)
            .where(DocumentDiffEvent.set_id == set_id)
            .order_by(DocumentDiffEvent.detected_at.desc())
            .limit(100)
        )
    ).scalars().all()

    return [
        DocumentDiffEventOut(
            id=event.id,
            set_id=event.set_id,
            left_document_id=event.left_document_id,
            right_document_id=event.right_document_id,
            left_label=labels.get(event.left_document_id, "Document A"),
            right_label=labels.get(event.right_document_id, "Document B"),
            unified_diff=event.unified_diff,
            change_summary=event.change_summary,
            is_meaningful=event.is_meaningful,
            detected_at=event.detected_at,
            viewed_at=event.viewed_at,
        )
        for event in rows
    ]


async def _set_out(db: AsyncSession, watched: WatchedSet) -> WatchedSetOut:
    documents = (
        await db.execute(
            select(WatchedDocument)
            .where(WatchedDocument.set_id == watched.id)
            .order_by(WatchedDocument.created_at.asc())
        )
    ).scalars().all()
    unread = (
        await db.execute(
            select(func.count())
            .select_from(DocumentDiffEvent)
            .where(
                DocumentDiffEvent.set_id == watched.id,
                DocumentDiffEvent.is_meaningful.is_(True),
                DocumentDiffEvent.viewed_at.is_(None),
            )
        )
    ).scalar_one()
    latest = (
        await db.execute(
            select(func.max(DocumentDiffEvent.detected_at)).where(
                DocumentDiffEvent.set_id == watched.id
            )
        )
    ).scalar_one()
    return WatchedSetOut(
        id=watched.id,
        name=watched.name,
        created_at=watched.created_at,
        last_viewed_at=watched.last_viewed_at,
        documents=[await _document_out(db, doc) for doc in documents],
        unread_meaningful=int(unread or 0),
        latest_event_at=latest,
    )


@router.get(
    "/skills/live-doc-diff/sets",
    response_model=list[WatchedSetOut],
    summary="List watched document sets",
)
async def list_sets(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WatchedSetOut]:
    rows = (
        await db.execute(
            select(WatchedSet)
            .where(WatchedSet.user_id == user_id)
            .order_by(WatchedSet.created_at.desc())
        )
    ).scalars().all()
    return [await _set_out(db, row) for row in rows]


@router.post(
    "/skills/live-doc-diff/sets",
    response_model=WatchedSetOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a watched set",
)
async def create_set(
    payload: WatchedSetIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchedSetOut:
    watched = WatchedSet(user_id=user_id, name=payload.name)
    db.add(watched)
    await db.commit()
    await db.refresh(watched)
    return await _set_out(db, watched)


@router.get(
    "/skills/live-doc-diff/sets/{set_id}",
    response_model=WatchedSetDetailOut,
    summary="Watched set with divergence timeline",
)
async def get_set(
    set_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchedSetDetailOut:
    watched = await _owned_set(db, set_id, user_id)
    base = await _set_out(db, watched)
    return WatchedSetDetailOut(
        **base.model_dump(),
        events=await _events_for_set(db, set_id),
    )


@router.delete(
    "/skills/live-doc-diff/sets/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a watched set",
)
async def delete_set(
    set_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    watched = await _owned_set(db, set_id, user_id)
    await db.delete(watched)
    await db.commit()


@router.post(
    "/skills/live-doc-diff/sets/{set_id}/documents",
    response_model=WatchedDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a document URL to a watched set",
)
async def add_document(
    set_id: uuid.UUID,
    payload: WatchedDocumentIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchedDocumentOut:
    watched = await _owned_set(db, set_id, user_id)
    document = WatchedDocument(
        set_id=watched.id,
        user_id=user_id,
        label=_label_from_url(payload.source_url, payload.label),
        source_url=payload.source_url,
    )
    db.add(document)
    await db.flush()

    text = (payload.text or "").strip()
    event_id = None
    if not text:
        text_from_capture, event_id = await service.latest_capture_text(
            db, user_id, payload.source_url
        )
        text = text_from_capture or ""
    if text:
        await service.add_snapshot(
            db, document, text, capture_event_id=event_id
        )

    await db.commit()
    await db.refresh(document)
    return await _document_out(db, document)


@router.delete(
    "/skills/live-doc-diff/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove a document from its watched set",
)
async def delete_document(
    document_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    document = await _owned_document(db, document_id, user_id)
    await db.delete(document)
    await db.commit()


@router.post(
    "/skills/live-doc-diff/documents/{document_id}/snapshots",
    response_model=WatchedDocumentOut,
    summary="Record a manual text snapshot",
)
async def post_snapshot(
    document_id: uuid.UUID,
    payload: SnapshotIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchedDocumentOut:
    document = await _owned_document(db, document_id, user_id)
    await service.add_snapshot(db, document, payload.text.strip())
    await db.commit()
    await db.refresh(document)
    return await _document_out(db, document)


@router.post(
    "/skills/live-doc-diff/sets/{set_id}/scan",
    response_model=WatchedSetDetailOut,
    summary="Refresh snapshots and compute diffs",
)
async def scan_set(
    set_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchedSetDetailOut:
    watched = await _owned_set(db, set_id, user_id)
    await service.scan_watched_set(db, watched)
    await db.commit()
    await db.refresh(watched)
    base = await _set_out(db, watched)
    return WatchedSetDetailOut(
        **base.model_dump(),
        events=await _events_for_set(db, set_id),
    )


@router.post(
    "/skills/live-doc-diff/sets/{set_id}/viewed",
    response_model=WatchedSetOut,
    summary="Mark divergence events as viewed",
)
async def mark_viewed(
    set_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WatchedSetOut:
    watched = await _owned_set(db, set_id, user_id)
    await service.mark_set_viewed(db, watched)
    await db.commit()
    await db.refresh(watched)
    return await _set_out(db, watched)


@router.get(
    "/skills/live-doc-diff/unread",
    response_model=UnreadCountOut,
    summary="Count unread meaningful divergence events",
)
async def unread_count(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UnreadCountOut:
    count = await service.unread_meaningful_count(db, user_id)
    return UnreadCountOut(unread_meaningful=count)
