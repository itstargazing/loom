"""Shared consume loop for stream-backed workers."""

import asyncio
import logging
import os
import socket
from collections.abc import Awaitable, Callable

from app.core.config import settings
from app.core.streams import RedisStream, StreamEntry

logger = logging.getLogger(__name__)

#  Pause after an unexpected failure, so a persistent outage does not become a
#  hot loop.
ERROR_BACKOFF_SECONDS = 5.0

Handler = Callable[[list[StreamEntry]], Awaitable[None]]


def consumer_name(prefix: str) -> str:
    """Unique per process, so several workers can share one group safely."""
    return f"{prefix}-{socket.gethostname()}-{os.getpid()}"


async def consume(
    *,
    stream: RedisStream,
    handler: Handler,
    stop_event: asyncio.Event,
    name: str,
    batch_size: int | None = None,
) -> None:
    batch_size = batch_size or settings.worker_batch_size
    consumer = consumer_name(name)
    await stream.ensure_group()
    logger.info("%s worker %s started", name, consumer)

    while not stop_event.is_set():
        try:
            # Recover anything a dead worker abandoned before taking new work.
            entries = await stream.claim_stale(
                consumer,
                min_idle_ms=settings.worker_claim_min_idle_ms,
                count=batch_size,
            )
            if not entries:
                entries = await stream.read_new(
                    consumer,
                    count=batch_size,
                    block_ms=settings.worker_block_ms,
                )

            if entries:
                await handler(entries)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("%s worker loop failed; backing off", name)
            await asyncio.sleep(ERROR_BACKOFF_SECONDS)

    logger.info("%s worker %s stopped", name, consumer)
