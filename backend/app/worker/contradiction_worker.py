"""Periodic contradiction watcher.

Not a Redis stream consumer — it polls recent claims on a timer because pairing
is a cross-event job rather than a reaction to one capture.
"""

from __future__ import annotations

import asyncio
import logging

from app.ai import get_ai_client
from app.core.config import settings
from app.core.database import async_session_factory
from app.services.contradiction_watcher import scan_all_users

logger = logging.getLogger(__name__)


async def run(stop_event: asyncio.Event) -> None:
    logger.info("contradiction watcher started")
    #  First pass soon after boot so a fresh seed shows pairs without a long wait.
    interval = max(5.0, settings.contradiction_watch_interval_seconds)
    first_delay = min(5.0, interval)

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=first_delay)
        return
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        try:
            client = get_ai_client()
            async with async_session_factory() as session:
                written = await scan_all_users(session, client)
            if written:
                logger.info("Contradiction watcher flagged %s pair(s)", written)
        except Exception:
            logger.exception("Contradiction watcher pass failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            continue

    logger.info("contradiction watcher stopped")
