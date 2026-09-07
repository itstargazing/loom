"""Classifies persisted capture events and routes them into the skill stores."""

import asyncio
import logging
from uuid import UUID

from app.ai import get_ai_client, get_local_ai_client
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.streams import StreamEntry
from app.models.privacy import UserPrivacySettings
from app.services.capture_text import capture_snippet
from app.services.classification import ClassificationOutcome, classify_event
from app.services.classification_cache import cache_key, get_cached_result, set_cached_result
from app.services.classification_queue import classification_stream, parse_entry
from app.services.classification_store import (
    already_handled,
    load_classifiable_event,
    mark_routed,
    record_outcome,
)
from app.services.embeddings import upsert_embedding
from app.services.skill_router import (
    RoutingContext,
    RoutingOutcome,
    route_classification,
    route_extracted_deadlines,
    route_extracted_readings,
)
from app.services.auto_attach_index import index_page_opened
from app.services.deadline_extract import extract_deadlines
from app.services.local_mode import matches_local_domain, normalize_domain_pattern
from app.services.reading_extract import extract_dwell_passages
from app.worker.loop import consume
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def classify_and_route(capture_event_id: UUID, queued_user_id: str) -> bool:
    """Classify and route one event. False means the entry should stay pending.

    Public because `scripts/seed_demo_data.py` drives the same path without
    Redis; seeding through a copy of this logic would let the two diverge.
    """
    async with async_session_factory() as session:
        if await already_handled(session, capture_event_id):
            logger.debug("Event %s already handled; skipping", capture_event_id)
            return True

        loaded = await load_classifiable_event(session, capture_event_id)

    if loaded is None:
        # The event was deleted between queueing and now, so there is nothing
        # to retry.
        logger.warning("Capture event %s no longer exists", capture_event_id)
        return True

    user_id, event = loaded
    owner = user_id or queued_user_id

    async with async_session_factory() as session:
        privacy = (
            await session.execute(
                select(UserPrivacySettings).where(
                    UserPrivacySettings.user_id == owner
                )
            )
        ).scalar_one_or_none()
    domain_patterns = [
        normalize_domain_pattern(item)
        for item in [
            *(privacy.local_only_domains if privacy else []),
            *settings.local_only_domains_default,
        ]
        if normalize_domain_pattern(item)
    ]
    use_local = matches_local_domain(event.source_url, domain_patterns)
    client = get_local_ai_client() if use_local else get_ai_client()
    snippet = capture_snippet(event.event_type, event.payload)
    cached = None if use_local else await get_cached_result(
        cache_key(user_id=owner, event_type=event.event_type, snippet=snippet)
    )
    if cached is not None:
        outcome = ClassificationOutcome(
            result=cached,
            attempts=0,
            provider="cache",
            model="redis",
            latency_ms=0,
            error=None,
            raw_text=cached.model_dump_json(),
            cached=True,
        )
        logger.info("Classification cache hit for %s", capture_event_id)
    else:
        if use_local:
            logger.info(
                "Classifying %s in local mode (no cloud AI) for %s",
                capture_event_id,
                event.source_url,
            )
        outcome = await classify_event(event, client)
        if outcome.succeeded and outcome.result is not None and not use_local:
            await set_cached_result(
                cache_key(user_id=owner, event_type=event.event_type, snippet=snippet),
                outcome.result,
            )

    async with async_session_factory() as session:
        review_status = await record_outcome(
            session,
            capture_event_id=capture_event_id,
            user_id=user_id or queued_user_id,
            outcome=outcome,
            snippet=snippet,
        )

    if not outcome.succeeded or outcome.result is None:
        # The failure is recorded either way. Leaving the entry unacknowledged
        # lets a provider outage be retried once the entry goes stale.
        logger.warning("Classification of %s failed: %s", capture_event_id, outcome.error)
        return False

    payload = event.payload or {}
    context_text = str(payload.get("context") or "").strip()

    context = RoutingContext(
        user_id=user_id or queued_user_id,
        capture_event_id=capture_event_id,
        source_url=event.source_url,
        page_title=event.page_title,
        context_text=context_text,
        occurred_at=event.occurred_at,
    )

    result = outcome.result
    threshold = settings.classification_auto_route_min_confidence
    high_items = [
        item
        for item in result.classifications
        if item.category == "none" or item.confidence >= threshold
    ]
    result = result.model_copy(update={"classifications": high_items})
    extracted_deadlines = []
    extracted_readings = []
    if event.event_type == "page_opened":
        page_text = str(payload.get("fullText") or "")
        extracted_deadlines = extract_deadlines(
            page_text,
            page_title=event.page_title,
            source_url=event.source_url,
            occurred_at=event.occurred_at,
        )
        if extracted_deadlines:
            # The extractor owns every date on the page; the single classification
            # item would otherwise duplicate the first one under the page title.
            kept = [
                item
                for item in result.classifications
                if item.category != "deadline"
            ]
            result = result.model_copy(update={"classifications": kept})
    elif event.event_type == "scroll_dwell":
        extracted_readings = extract_dwell_passages(payload)
        if extracted_readings:
            #  Extractor keeps heading + dwell_ms for every qualifying section.
            kept = [
                item
                for item in result.classifications
                if item.category != "reading_highlight"
            ]
            result = result.model_copy(update={"classifications": kept})

    async with async_session_factory() as session:
        if event.event_type == "page_opened":
            await index_page_opened(
                session,
                user_id=context.user_id,
                source_url=event.source_url,
                page_title=event.page_title,
                payload=payload,
            )
        routed = await route_classification(session, result, context)
        if extracted_deadlines:
            extra = await route_extracted_deadlines(
                session,
                [item for item in extracted_deadlines if item.confidence >= threshold],
                context,
            )
            routed = RoutingOutcome(
                entries=[*routed.entries, *extra.entries],
                skipped=routed.skipped,
            )
        if extracted_readings:
            extra = await route_extracted_readings(
                session, extracted_readings, context
            )
            routed = RoutingOutcome(
                entries=[*routed.entries, *extra.entries],
                skipped=routed.skipped,
            )
        # Pending review stays un-routed so digest accept can finish the write.
        if review_status != "pending_review":
            await mark_routed(session, capture_event_id)
        await upsert_embedding(
            session,
            capture_event_id=capture_event_id,
            user_id=context.user_id,
            snippet=snippet,
        )

    logger.info(
        "Classified %s as %s: %s new, %s merged, %s skipped (%sms)",
        capture_event_id,
        outcome.result.categories,
        routed.created_count,
        routed.merged_count,
        len(routed.skipped),
        outcome.latency_ms,
    )
    return True


async def handle(entries: list[StreamEntry]) -> None:
    done_ids: list[str] = []

    for entry_id, fields in entries:
        try:
            user_id, capture_event_id = parse_entry(fields)
        except Exception:
            logger.exception("Dropping malformed classification entry %s", entry_id)
            done_ids.append(entry_id)
            continue

        try:
            if await classify_and_route(capture_event_id, user_id):
                done_ids.append(entry_id)
        except Exception:
            logger.exception("Unexpected error classifying entry %s", entry_id)

    await classification_stream.ack(done_ids)


async def run(stop_event: asyncio.Event) -> None:
    await consume(
        stream=classification_stream,
        handler=handle,
        stop_event=stop_event,
        name="classification",
        batch_size=settings.classification_batch_size,
    )
