import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EventClassification(Base):
    """The classifier's decision about one capture event.

    Phase 3.1 stops here: the decision is logged against the originating event
    but not yet written into any skill store.
    """

    __tablename__ = "event_classifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    #  Unique, so reprocessing the same event updates its row instead of
    #  accumulating duplicates under at-least-once delivery.
    capture_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("capture_events.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    #  "succeeded" or "failed".
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)

    #  Flattened for cheap filtering; the full result stays in `result`.
    categories: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    #  Raw model output kept even on success so digest/privacy receipts can
    #  show exactly what the model said.
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #  pending_review | auto_routed | accepted | reassigned | discarded
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="auto_routed")

    #  Set once the result has been written into the typed skill stores. Null
    #  means classified but not yet routed, which is a resumable state.
    routed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_event_classifications_user_created", "user_id", "created_at"),
        Index("ix_event_classifications_status", "status"),
        Index("ix_event_classifications_categories", "categories", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<EventClassification {self.status} {self.categories}>"
