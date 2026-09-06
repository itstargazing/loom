"""Smart File Auto-Attach: recent document index and field matching."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.auto_attach import RecentDocument
from app.schemas.auto_attach import (
    AutoAttachMatchOut,
    AutoAttachMatchRequest,
    AutoAttachMatchResponse,
    RecentDocumentIn,
    RecentDocumentOut,
)
from app.services.auto_attach_index import get_owned_document, upsert_recent_document
from app.services.auto_attach_match import rank_documents
from app.services.form_pdf import resolve_stored_path

router = APIRouter(prefix="/api", tags=["auto-attach"])


def _out(row: RecentDocument) -> RecentDocumentOut:
    return RecentDocumentOut(
        id=row.id,
        filename=row.filename,
        source_url=row.source_url,
        doc_type=row.doc_type,
        summary=row.summary,
        mime_type=row.mime_type,
        has_file=bool(row.storage_path),
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
    )


@router.get(
    "/skills/auto-attach/documents",
    response_model=list[RecentDocumentOut],
    summary="List recently indexed documents",
)
async def list_documents(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[RecentDocumentOut]:
    rows = (
        await db.execute(
            select(RecentDocument)
            .where(RecentDocument.user_id == user_id)
            .order_by(RecentDocument.last_seen_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [_out(row) for row in rows]


@router.post(
    "/skills/auto-attach/documents",
    response_model=RecentDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Index a document for attach suggestions",
)
async def create_document(
    payload: RecentDocumentIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecentDocumentOut:
    row = await upsert_recent_document(
        db,
        user_id=user_id,
        filename=payload.filename,
        source_url=payload.source_url,
        doc_type=payload.doc_type,
        summary=payload.summary,
        mime_type=payload.mime_type,
    )
    await db.commit()
    await db.refresh(row)
    return _out(row)


@router.delete(
    "/skills/auto-attach/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove a document from the index",
)
async def delete_document(
    document_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    row = await get_owned_document(db, document_id, user_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    await db.delete(row)
    await db.commit()


@router.post(
    "/skills/auto-attach/match",
    response_model=AutoAttachMatchResponse,
    summary="Match an upload field against the recent-document index",
)
async def match_field(
    payload: AutoAttachMatchRequest,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutoAttachMatchResponse:
    rows = (
        await db.execute(
            select(RecentDocument)
            .where(RecentDocument.user_id == user_id)
            .order_by(RecentDocument.last_seen_at.desc())
            .limit(100)
        )
    ).scalars().all()
    ranked = rank_documents(
        label_text=payload.label_text,
        surrounding_text=payload.surrounding_text,
        field_name=payload.field_name,
        accept=payload.accept,
        documents=[
            (
                row.id,
                row.filename,
                row.doc_type,
                row.source_url,
                row.summary,
                row.storage_path,
                row.mime_type,
            )
            for row in rows
        ],
    )
    candidates = [
        AutoAttachMatchOut(
            document_id=uuid.UUID(str(item.document_id)),
            filename=item.filename,
            doc_type=item.doc_type,
            source_url=item.source_url,
            summary=item.summary,
            has_file=item.has_file,
            confidence=item.confidence,
            reason=item.reason,
        )
        for item in ranked[:5]
    ]
    return AutoAttachMatchResponse(
        match=candidates[0] if candidates else None,
        candidates=candidates,
    )


@router.get(
    "/skills/auto-attach/documents/{document_id}/file",
    summary="Download indexed file bytes when available",
)
async def download_file(
    document_id: uuid.UUID,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FileResponse:
    row = await get_owned_document(db, document_id, user_id)
    if row is None or not row.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cached file for this document",
        )
    path = resolve_stored_path(settings.form_storage_dir, row.storage_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Stored file is missing",
        )
    media = row.mime_type or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=row.filename)
