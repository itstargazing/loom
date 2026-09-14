"""Periodic retention purge for captures and skill stores."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.capture_event import CaptureEvent
from app.models.event_classification import EventClassification
from app.models.skill_stores import (
    Citation,
    ContractFlag,
    Contradiction,
    ContradictionClaim,
    Deadline,
    GlossaryTerm,
    JobListing,
    ProductListing,
    ReadingCompilerEntry,
)

logger = logging.getLogger(__name__)


async def purge_expired(*, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    counts: dict[str, int] = {}

    async with async_session_factory() as session:
        if settings.capture_retention_days > 0:
            cutoff = now - timedelta(days=settings.capture_retention_days)
            # Classifications reference captures; drop them first by age on created_at/occurred.
            result = await session.execute(
                delete(EventClassification).where(EventClassification.created_at < cutoff)
            )
            counts["event_classifications"] = int(result.rowcount or 0)
            result = await session.execute(
                delete(CaptureEvent).where(CaptureEvent.occurred_at < cutoff)
            )
            counts["capture_events"] = int(result.rowcount or 0)

        if settings.skill_retention_days > 0:
            skill_cutoff = now - timedelta(days=settings.skill_retention_days)
            for model, label, column in (
                (Citation, "citations", Citation.created_at),
                (Deadline, "deadlines", Deadline.created_at),
                (GlossaryTerm, "glossary_terms", GlossaryTerm.created_at),
                (ReadingCompilerEntry, "reading_compiler_entries", ReadingCompilerEntry.created_at),
                (ProductListing, "product_listings", ProductListing.created_at),
                (JobListing, "job_listings", JobListing.created_at),
                (ContractFlag, "contract_flags", ContractFlag.created_at),
                (Contradiction, "contradictions", Contradiction.created_at),
                (ContradictionClaim, "contradiction_claims", ContradictionClaim.created_at),
            ):
                try:
                    result = await session.execute(delete(model).where(column < skill_cutoff))
                    counts[label] = int(result.rowcount or 0)
                except Exception:
                    logger.exception("Retention purge failed for %s", label)

        await session.commit()

    return counts


async def run(stop_event: asyncio.Event) -> None:
    logger.info(
        "Retention worker started (capture=%sd skill=%sd interval=%ss)",
        settings.capture_retention_days,
        settings.skill_retention_days,
        settings.retention_purge_interval_seconds,
    )
    while not stop_event.is_set():
        try:
            if settings.capture_retention_days > 0 or settings.skill_retention_days > 0:
                counts = await purge_expired()
                total = sum(counts.values())
                if total:
                    logger.info("Retention purged %s row(s): %s", total, counts)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Retention purge failed")

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=max(60.0, settings.retention_purge_interval_seconds),
            )
        except asyncio.TimeoutError:
            continue

    logger.info("Retention worker stopped")
