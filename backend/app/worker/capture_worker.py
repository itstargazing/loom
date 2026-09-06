"""Persists queued capture events, then queues them for classification."""

import asyncio
import logging

from app.core.database import async_session_factory
from app.core.streams import StreamEntry
from app.services.capture_ingest import persist_capture_events
from app.services.capture_queue import capture_stream, parse_entry
from app.services.classification_queue import enqueue_for_classification
from app.worker.loop import consume

logger = logging.getLogger(__name__)


async def handle(entries: list[StreamEntry]) -> None:
    parsed = []
    poison_ids: list[str] = []

    for entry_id, fields in entries:
        try:
            parsed.append(parse_entry(fields))
        except Exception:
            # Malformed entries will never succeed, so acknowledge and drop them
            # rather than redelivering forever.
            logger.exception("Dropping malformed capture entry %s", entry_id)
            poison_ids.append(entry_id)

    await capture_stream.ack(poison_ids)

    if not parsed:
        return

    async with async_session_factory() as session:
        inserted = await persist_capture_events(session, parsed)

    if inserted:
        await enqueue_for_classification(inserted)

    # Acknowledged only after the commit; a crash before this point leaves the
    # entries pending for another worker to reclaim.
    poison = set(poison_ids)
    await capture_stream.ack([entry_id for entry_id, _ in entries if entry_id not in poison])

    logger.info("Stored %s new event(s) from a batch of %s", len(inserted), len(parsed))


async def run(stop_event: asyncio.Event) -> None:
    await consume(
        stream=capture_stream,
        handler=handle,
        stop_event=stop_event,
        name="capture",
    )
