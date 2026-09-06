"""Per-user privacy settings for local-only classification domains."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserPrivacySettings(Base):
    __tablename__ = "user_privacy_settings"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    #  Hostname suffixes / exact hosts that force local (non-cloud) classification.
    local_only_domains: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
