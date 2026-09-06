"""Watched document sets and detected divergence events."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WatchedSet(Base):
    """A named group of documents compared for divergence."""

    __tablename__ = "watched_sets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (Index("ix_watched_sets_user", "user_id"),)


class WatchedDocument(Base):
    """One document URL inside a watched set."""

    __tablename__ = "watched_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("watched_sets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_watched_documents_set", "set_id"),
        Index("ix_watched_documents_user_url", "user_id", "source_url"),
    )


class DocumentSnapshot(Base):
    """A point-in-time text capture of a watched document."""

    __tablename__ = "document_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("watched_documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    capture_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("capture_events.id", ondelete="SET NULL"), nullable=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_document_snapshots_document_captured", "document_id", "captured_at"),
    )


class DocumentDiffEvent(Base):
    """A detected divergence between two documents in a set."""

    __tablename__ = "document_diff_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("watched_sets.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    left_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("watched_documents.id", ondelete="CASCADE"), nullable=False
    )
    right_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("watched_documents.id", ondelete="CASCADE"), nullable=False
    )
    left_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    right_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("document_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    unified_diff: Mapped[str] = mapped_column(Text, nullable=False, default="")
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_meaningful: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_document_diff_events_set_detected", "set_id", "detected_at"),
        Index("ix_document_diff_events_user_unread", "user_id", "viewed_at"),
    )
