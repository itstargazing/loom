"""Direct persist + classify when Redis is unavailable.

The normal path is ingest → Redis stream → worker. On a machine without Redis
(common on Windows without Docker/WSL) that path never leaves the queue, so
captures would appear accepted and then vanish. This fallback writes the same
rows the worker would have written, then classifies in the background so a
large extension batch cannot stall the HTTP response.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from app.core.database import async_session_factory
from app.schemas.capture import CaptureEventIn
from app.services.capture_ingest import persist_capture_events

logger = logging.getLogger(__name__)

_background: set[asyncio.Task[None]] = set()


async def persist_and_classify_inline(user_id: str, events: list[CaptureEventIn]) -> int:
    """Store events in Postgres, then classify new rows off the request path."""
    async with async_session_factory() as session:
        inserted = await persist_capture_events(
            session, [(user_id, event) for event in events]
        )

    if inserted:
        task = asyncio.create_task(_classify_many(inserted))
        _background.add(task)
        task.add_done_callback(_background.discard)

    return len(events)


async def _classify_many(pairs: list[tuple[str, UUID]]) -> None:
    from app.worker.classification_worker import classify_and_route

    for owner, event_id in pairs:
        try:
            await classify_and_route(event_id, owner)
        except Exception:
            logger.exception("Inline classification failed for %s", event_id)
