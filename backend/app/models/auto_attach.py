"""Index of recently seen documents for Smart File Auto-Attach."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

DOC_TYPES = (
    "resume",
    "id_scan",
    "transcript",
    "pdf",
    "image",
    "other",
)


class RecentDocument(Base):
    """A file the user opened, uploaded, or indexed for attach suggestions."""

    __tablename__ = "recent_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False, default="other")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    #  Relative path under form/auto-attach storage when bytes are available.
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "source_url", "filename", name="uq_recent_documents_user_url_name"
        ),
        Index("ix_recent_documents_user_seen", "user_id", "last_seen_at"),
    )
