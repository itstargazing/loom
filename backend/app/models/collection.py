import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Collection(Base):
    """A user-named grouping that skill entries can be filed under.

    Optional everywhere: an entry with no collection is simply unfiled. Grouping
    is metadata and never part of an entry's identity, so the same term is not
    stored twice just because it was filed differently.
    """

    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_collections_user_name"),
    )

    def __repr__(self) -> str:
        return f"<Collection {self.name!r}>"
