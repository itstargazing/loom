"""Tables for Ask, digest corrections, briefs, and nudges."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClassificationCorrection(Base):
    """Human-labeled replacement for a model classification (training data)."""

    __tablename__ = "classification_corrections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    capture_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("capture_events.id", ondelete="CASCADE"), nullable=False
    )
    original_categories: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    corrected_category: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_classification_corrections_user", "user_id", "created_at"),)


class CaptureEmbedding(Base):
    """Vector for one capture event. Stored as float array so tests need no pgvector wheel."""

    __tablename__ = "capture_embeddings"

    capture_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("capture_events.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_capture_embeddings_user", "user_id"),)


class ResearchBrief(Base):
    __tablename__ = "research_briefs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    source_event_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    deadline_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_research_briefs_user", "user_id", "created_at"),)


class DashboardNotification(Base):
    __tablename__ = "dashboard_notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    href: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_dashboard_notifications_user", "user_id", "created_at"),)


class DeadlineNudgeLog(Base):
    """Rate-limit: one nudge per deadline per day."""

    __tablename__ = "deadline_nudge_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    deadline_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    day: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "deadline_id", "day", name="uq_deadline_nudge_day"),
    )
