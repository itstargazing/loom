"""Routes a validated classification into the typed skill stores.

Adding a skill means adding one :class:`SkillRoute` to ``ROUTES``; the pipeline
itself never changes. A category with no route (``none``) is skipped.

Writes are upserts on ``(user_id, dedup_key)``. Re-capturing something already
stored bumps ``times_seen`` and appends a sighting rather than inserting a
duplicate, which is what makes routing safe to retry — and it must be, because
the queue delivers at least once.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_stores import (
    Citation,
    ContractFlag,
    ContradictionClaim,
    Deadline,
    GlossaryTerm,
    JobListing,
    ProductListing,
    ReadingCompilerEntry,
)
from app.schemas.classification import (
    ClassificationItem,
    ClassificationResult,
    ExtractedFields,
    SkillCategory,
)
from app.services.citation_format import CitationMeta, format_styles
from app.services.deadline_extract import CONFIRMED_AT, document_identity
from app.services.deadline_parse import date_identity, parse_due
from app.services.dedup import dedup_key

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RoutingContext:
    """Everything about the originating event a store row might need."""

    user_id: str
    capture_event_id: UUID | None
    source_url: str
    page_title: str
    collection_id: UUID | None = None
    # Surrounding paragraph from the capture payload, used as the glossary
    # "seen in this context" snippet when the model did not extract a passage.
    context_text: str = ""
    occurred_at: str | None = None


#  Identity: which normalised values make two captures the same entry.
KeyBuilder = Callable[[ExtractedFields, RoutingContext], tuple[str | None, ...]]
#  Skill-specific columns. Envelope columns are added centrally. Context is
#  passed so a store can keep originating text that the model did not extract
#  (glossary context snippets, for example).
ColumnBuilder = Callable[[ExtractedFields, RoutingContext], dict[str, Any]]


@dataclass(slots=True)
class SkillRoute:
    """How one category becomes a row in one store."""

    model: Any
    key: KeyBuilder
    columns: ColumnBuilder


ROUTES: dict[SkillCategory, SkillRoute] = {
    "glossary_term": SkillRoute(
        model=GlossaryTerm,
        # Term only: the same term on ten pages is one entry with ten sightings.
        key=lambda fields, context: (fields.term,),
        columns=lambda fields, context: {
            "term": fields.term,
            "definition": fields.definition,
            "context_snippet": (fields.passage or context.context_text or "").strip(),
        },
    ),
    "citation": SkillRoute(
        model=Citation,
        # The quote alone, so one passage reached via two URLs is not duplicated.
        key=lambda fields, context: (fields.quote,),
        columns=lambda fields, context: _citation_columns(fields, context),
    ),
    "deadline": SkillRoute(
        model=Deadline,
        # Title + resolved date + document stem, so two versions of the same
        # syllabus merge, while two courses sharing "Problem Set 3" do not.
        key=lambda fields, context: (
            fields.deadline_title,
            date_identity(fields.deadline_date or "", occurred_at=context.occurred_at),
            document_identity(context.source_url),
        ),
        columns=lambda fields, context: _deadline_columns(fields, context),
    ),
    "contradiction_candidate": SkillRoute(
        model=ContradictionClaim,
        # Source is part of identity here: the whole point is spotting one topic
        # claimed differently by different sources.
        key=lambda fields, context: (fields.claim, context.source_url),
        columns=lambda fields, _context: {"claim": fields.claim, "topic": fields.topic},
    ),
    "reading_highlight": SkillRoute(
        model=ReadingCompilerEntry,
        key=lambda fields, context: (fields.passage, context.source_url),
        columns=lambda fields, _context: {
            "passage": fields.passage,
            "heading": fields.reading_heading,
            "dwell_ms": int(fields.reading_dwell_ms or 0),
        },
    ),
    "product_listing": SkillRoute(
        model=ProductListing,
        # A listing page is one product; revisiting updates rather than adds.
        key=lambda fields, context: (context.source_url, fields.product_name),
        columns=lambda fields, _context: {
            "name": fields.product_name,
            "price": fields.price,
            "specs": {spec.name: spec.value for spec in fields.specs or []},
        },
    ),
    "job_listing": SkillRoute(
        model=JobListing,
        key=lambda fields, context: (context.source_url, fields.job_title),
        columns=lambda fields, _context: {
            "title": fields.job_title,
            "company": fields.company,
            "salary": fields.salary,
            "requirements": fields.requirements or [],
            "application_deadline": fields.application_deadline,
        },
    ),
    "contract_clause": SkillRoute(
        model=ContractFlag,
        key=lambda fields, context: (fields.clause_text, context.source_url),
        columns=lambda fields, _context: {
            "clause_text": fields.clause_text,
            "flag_reason": fields.flag_reason,
            "risk_level": fields.risk_level,
        },
    ),
}


def _deadline_columns(fields: ExtractedFields, context: RoutingContext) -> dict[str, Any]:
    due_text = (fields.deadline_date or "").strip()
    return {
        "title": fields.deadline_title,
        "due_text": due_text,
        "due_date": parse_due(due_text, occurred_at=context.occurred_at),
        "kind": fields.deadline_kind,
        "context_snippet": (context.context_text or "").strip(),
        "confirmed": False,
    }


def _citation_columns(fields: ExtractedFields, context: RoutingContext) -> dict[str, Any]:
    """Bibliographic fields plus APA/MLA strings derived from them."""
    work_title = (fields.work_title or context.page_title or "").strip() or None
    return {
        "quote": fields.quote,
        "author": fields.author,
        "work_title": work_title,
        "publisher": fields.publisher,
        "published_date": fields.published_date,
        "formatted": format_styles(
            CitationMeta(
                author=fields.author,
                work_title=work_title,
                publisher=fields.publisher,
                published_date=fields.published_date,
                source_url=context.source_url,
                page_title=context.page_title,
            )
        ),
    }


@dataclass(slots=True)
class RoutedEntry:
    category: SkillCategory
    table: str
    entry_id: UUID
    created: bool


@dataclass(slots=True)
class RoutingOutcome:
    entries: list[RoutedEntry]
    skipped: list[SkillCategory]

    @property
    def created_count(self) -> int:
        return sum(1 for entry in self.entries if entry.created)

    @property
    def merged_count(self) -> int:
        return sum(1 for entry in self.entries if not entry.created)


def build_upsert(
    route: SkillRoute,
    item: ClassificationItem,
    context: RoutingContext,
    *,
    now: datetime | None = None,
):
    """Build the upsert for one classification item.

    Separated from execution so the generated SQL can be asserted in tests
    without a live database.
    """
    model = route.model
    now = now or datetime.now(UTC)

    sighting = {
        "sourceUrl": context.source_url,
        "pageTitle": context.page_title,
        "seenAt": now.isoformat(),
        "captureEventId": (
            str(context.capture_event_id) if context.capture_event_id else None
        ),
        "confidence": item.confidence,
        "contextSnippet": context.context_text or None,
    }

    values: dict[str, Any] = {
        "id": uuid4(),
        "user_id": context.user_id,
        "capture_event_id": context.capture_event_id,
        "collection_id": context.collection_id,
        "dedup_key": dedup_key(*route.key(item.fields, context)),
        "source_url": context.source_url,
        "page_title": context.page_title,
        "confidence": item.confidence,
        "times_seen": 1,
        "occurrences": [],
        "last_seen_at": now,
        **route.columns(item.fields, context),
    }
    if model is Deadline:
        values["confirmed"] = item.confidence >= CONFIRMED_AT

    conflict_set: dict[str, Any] = {
        "times_seen": model.times_seen + 1,
        "last_seen_at": now,
        # jsonb || jsonb appends to the array, so sighting history
        # accumulates without reading the row first.
        "occurrences": model.occurrences.concat(cast([sighting], JSONB)),
        # Keep the best confidence ever seen for this entry.
        "confidence": func.greatest(model.confidence, item.confidence),
    }
    if model is ReadingCompilerEntry:
        conflict_set["dwell_ms"] = func.greatest(
            model.dwell_ms, values["dwell_ms"]
        )
        #  Prefer a non-empty heading when a later dwell supplies one.
        conflict_set["heading"] = func.coalesce(
            model.heading, values.get("heading")
        )

    return (
        insert(model)
        .values(values)
        .on_conflict_do_update(
            index_elements=[model.user_id, model.dedup_key],
            set_=conflict_set,
        )
        # times_seen comes back post-update, so 1 means this was an insert.
        .returning(model.id, model.times_seen)
    )


async def route_classification(
    session: AsyncSession,
    result: ClassificationResult,
    context: RoutingContext,
) -> RoutingOutcome:
    """Write every routable classification into its store.

    Commits once, so an event lands in all of its stores or none of them.
    """
    entries: list[RoutedEntry] = []
    skipped: list[SkillCategory] = []

    for item in result.classifications:
        route = ROUTES.get(item.category)
        if route is None:
            skipped.append(item.category)
            continue

        outcome = await session.execute(build_upsert(route, item, context))
        entry_id, times_seen = outcome.one()

        entries.append(
            RoutedEntry(
                category=item.category,
                table=route.model.__tablename__,
                entry_id=entry_id,
                created=times_seen == 1,
            )
        )

    await session.commit()

    return RoutingOutcome(entries=entries, skipped=skipped)


async def route_extracted_deadlines(
    session: AsyncSession,
    extracted: list,
    context: RoutingContext,
) -> RoutingOutcome:
    """Write every date the page-level extractor found.

    Each mention is its own upsert so two dates on one syllabus become two
    rows, and a second version of the same file merges rather than duplicates.
    """
    from app.services.deadline_extract import ExtractedDeadline

    entries: list[RoutedEntry] = []
    for item in extracted:
        if not isinstance(item, ExtractedDeadline):
            continue
        item_context = RoutingContext(
            user_id=context.user_id,
            capture_event_id=context.capture_event_id,
            source_url=context.source_url,
            page_title=context.page_title,
            collection_id=context.collection_id,
            context_text=item.context_snippet,
            occurred_at=context.occurred_at,
        )
        classified = ClassificationItem(
            category="deadline",
            confidence=item.confidence,
            reason="Extracted from a dated obligation on the page.",
            fields=ExtractedFields.of(
                deadline_title=item.title,
                deadline_date=item.due_text,
                deadline_kind=item.kind,  # type: ignore[arg-type]
            ),
        )
        outcome = await session.execute(
            build_upsert(ROUTES["deadline"], classified, item_context)
        )
        entry_id, times_seen = outcome.one()
        entries.append(
            RoutedEntry(
                category="deadline",
                table="deadlines",
                entry_id=entry_id,
                created=times_seen == 1,
            )
        )

    if entries:
        await session.commit()
    return RoutingOutcome(entries=entries, skipped=[])


async def route_extracted_readings(
    session: AsyncSession,
    extracted: list,
    context: RoutingContext,
) -> RoutingOutcome:
    """Write every dwell section that cleared the attention threshold."""
    from app.services.reading_extract import ExtractedPassage

    entries: list[RoutedEntry] = []
    for item in extracted:
        if not isinstance(item, ExtractedPassage):
            continue
        classified = ClassificationItem(
            category="reading_highlight",
            confidence=item.confidence,
            reason="Section cleared the reading dwell threshold.",
            fields=ExtractedFields.of(
                passage=item.passage,
                reading_heading=item.heading,
                reading_dwell_ms=item.dwell_ms,
            ),
        )
        outcome = await session.execute(
            build_upsert(ROUTES["reading_highlight"], classified, context)
        )
        entry_id, times_seen = outcome.one()
        entries.append(
            RoutedEntry(
                category="reading_highlight",
                table="reading_compiler_entries",
                entry_id=entry_id,
                created=times_seen == 1,
            )
        )

    if entries:
        await session.commit()
    return RoutingOutcome(entries=entries, skipped=[])
