import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CaptureEvent(Base):
    """A raw, unprocessed capture signal received from the extension."""

    __tablename__ = "capture_events"

    # Generated client-side, which makes extension retries and Redis stream
    # redeliveries idempotent: the same event can arrive more than once and
    # still produce exactly one row.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)

    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    page_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    referring_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    #  When the signal happened in the browser.
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #  When this API accepted it.
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_capture_events_user_occurred", "user_id", "occurred_at"),
        Index("ix_capture_events_user_type", "user_id", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<CaptureEvent {self.event_type} {self.id}>"
