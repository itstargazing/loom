"""The typed store each skill reads from.

All eight share the same envelope — owner, originating capture event, optional
collection, dedup key, and sighting counters — so it lives in one mixin rather
than being restated per table. Only the skill-specific columns differ.

Every entry keeps ``capture_event_id`` so any row can be traced back to the
browsing moment that produced it.

Identity is ``(user_id, dedup_key)``: a hash the router computes from whichever
fields make an entry "the same thing" for that skill. It deliberately excludes
``collection_id``, both because grouping is not identity and because Postgres
treats NULLs as distinct, which would silently defeat dedup for unfiled entries.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base

#  Hex-encoded truncated sha256. Fixed width, so it indexes well no matter how
#  long the underlying quote or clause is.
DEDUP_KEY_LENGTH = 32


class SkillEntry:
    """Columns shared by every skill store."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    @declared_attr
    @classmethod
    def capture_event_id(cls) -> Mapped[uuid.UUID]:
        """The browsing moment this entry came from.

        SET NULL rather than CASCADE on delete: purging raw capture history
        should not silently erase the structured output derived from it.
        """
        return mapped_column(
            Uuid, ForeignKey("capture_events.id", ondelete="SET NULL"), nullable=True
        )

    @declared_attr
    @classmethod
    def collection_id(cls) -> Mapped[uuid.UUID | None]:
        return mapped_column(
            Uuid, ForeignKey("collections.id", ondelete="SET NULL"), nullable=True
        )

    dedup_key: Mapped[str] = mapped_column(
        String(DEDUP_KEY_LENGTH), nullable=False
    )

    source_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    page_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    #  Bumped when the same thing is captured again, instead of inserting a
    #  duplicate row.
    times_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    #  Every sighting after the first, as {sourceUrl, pageTitle, seenAt, ...}.
    #  Phase 5's "seen in these contexts" view reads this.
    occurrences: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


def _shared_table_args(table: str) -> tuple:
    return (
        UniqueConstraint("user_id", "dedup_key", name=f"uq_{table}_user_dedup"),
        Index(f"ix_{table}_user_created", "user_id", "created_at"),
        Index(f"ix_{table}_collection", "collection_id"),
    )


class GlossaryTerm(SkillEntry, Base):
    __tablename__ = "glossary_terms"

    term: Mapped[str] = mapped_column(Text, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    #  The surrounding text the term was highlighted in, which is what the
    #  definition was generated from.
    context_snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = _shared_table_args("glossary_terms")


class Citation(SkillEntry, Base):
    __tablename__ = "citations"

    quote: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #  Rendered citation strings keyed by style, e.g. {"apa": "...", "mla": "..."}.
    #  Written by the router from extracted metadata; rebuilt if the user corrects it.
    formatted: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    __table_args__ = _shared_table_args("citations")


class Deadline(SkillEntry, Base):
    __tablename__ = "deadlines"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    #  Free text, not a date column: sources say "next Friday" or "end of term"
    #  as often as they give a parseable date. Phase 7 resolves these.
    due_text: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #  The sentence the date was taken from, so the calendar can show the
    #  original wording for verification.
    context_snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #  Low-confidence rows stay False until the person confirms them.
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = _shared_table_args("deadlines")


class ContradictionClaim(SkillEntry, Base):
    """One checkable claim, awaiting pairing.

    Separate from :class:`Contradiction` because a classification yields a single
    claim; a contradiction needs two from different sources. Phase 8 clusters
    these by topic and promotes conflicting pairs.
    """

    __tablename__ = "contradiction_claims"

    claim: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    __table_args__ = _shared_table_args("contradiction_claims")


class Contradiction(Base):
    """Two claims on one topic that disagree.

    Written by the contradiction watcher in Phase 8, not by the router.
    """

    __tablename__ = "contradictions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    claim_a: Mapped[str] = mapped_column(Text, nullable=False)
    claim_b: Mapped[str] = mapped_column(Text, nullable=False)
    source_a_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_b_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    claim_a_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("contradiction_claims.id", ondelete="SET NULL"), nullable=True
    )
    claim_b_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("contradiction_claims.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "claim_a_id", "claim_b_id", name="uq_contradictions_pair"),
        Index("ix_contradictions_user_created", "user_id", "created_at"),
        Index("ix_contradictions_user_dismissed", "user_id", "dismissed"),
    )


class ReadingCompilerEntry(SkillEntry, Base):
    __tablename__ = "reading_compiler_entries"

    passage: Mapped[str] = mapped_column(Text, nullable=False)
    dwell_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heading: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = _shared_table_args("reading_compiler_entries")


class ProductListing(SkillEntry, Base):
    __tablename__ = "product_listings"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    #  Free text, keeping the currency and formatting as written. Comparison in
    #  Phase 11 normalises it; storing a number here would lose information.
    price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #  Spec names vary wildly between retailers, so this stays schemaless.
    specs: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = _shared_table_args("product_listings")


class JobListing(SkillEntry, Base):
    __tablename__ = "job_listings"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    application_deadline: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = _shared_table_args("job_listings")


class ContractFlag(SkillEntry, Base):
    __tablename__ = "contract_flags"

    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    flag_reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = _shared_table_args("contract_flags")
