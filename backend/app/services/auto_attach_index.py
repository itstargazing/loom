"""Upsert helpers for the recent-document index."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auto_attach import RecentDocument
from app.services.auto_attach_match import infer_doc_type, summarize_text


def _filename_from_url(url: str, fallback: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name
    return name or fallback


async def upsert_recent_document(
    session: AsyncSession,
    *,
    user_id: str,
    filename: str,
    source_url: str = "",
    doc_type: str | None = None,
    summary: str = "",
    mime_type: str = "",
    storage_path: str | None = None,
) -> RecentDocument:
    filename = filename.strip() or "document"
    source_url = (source_url or "").strip()
    summary = summarize_text(summary) if summary else ""
    resolved_type = doc_type or infer_doc_type(filename, "", summary)

    existing = (
        await session.execute(
            select(RecentDocument).where(
                RecentDocument.user_id == user_id,
                RecentDocument.source_url == source_url,
                RecentDocument.filename == filename,
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if existing is None:
        row = RecentDocument(
            user_id=user_id,
            filename=filename,
            source_url=source_url,
            doc_type=resolved_type,
            summary=summary,
            mime_type=mime_type or "",
            storage_path=storage_path,
            last_seen_at=now,
        )
        session.add(row)
        await session.flush()
        return row

    existing.last_seen_at = now
    if summary:
        existing.summary = summary
    if resolved_type and resolved_type != "other":
        existing.doc_type = resolved_type
    if mime_type:
        existing.mime_type = mime_type
    if storage_path:
        existing.storage_path = storage_path
    await session.flush()
    return existing


async def index_page_opened(
    session: AsyncSession,
    *,
    user_id: str,
    source_url: str,
    page_title: str,
    payload: dict,
) -> RecentDocument | None:
    content_type = str(payload.get("contentType") or "").casefold()
    full_text = str(payload.get("fullText") or "")
    if content_type != "pdf" and not source_url.casefold().endswith(".pdf"):
        return None

    filename = _filename_from_url(source_url, page_title or "document.pdf")
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    return await upsert_recent_document(
        session,
        user_id=user_id,
        filename=filename,
        source_url=source_url,
        doc_type=infer_doc_type(filename, page_title, full_text),
        summary=full_text or page_title,
        mime_type="application/pdf",
    )


async def index_form_document(
    session: AsyncSession,
    *,
    user_id: str,
    filename: str,
    source_url: str,
    storage_path: str,
) -> RecentDocument:
    return await upsert_recent_document(
        session,
        user_id=user_id,
        filename=filename,
        source_url=source_url,
        doc_type=infer_doc_type(filename, "", ""),
        summary=f"Fillable PDF uploaded as {filename}",
        mime_type="application/pdf",
        storage_path=storage_path,
    )


async def get_owned_document(
    session: AsyncSession, document_id: uuid.UUID, user_id: str
) -> RecentDocument | None:
    result = await session.execute(
        select(RecentDocument).where(
            RecentDocument.id == document_id,
            RecentDocument.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
