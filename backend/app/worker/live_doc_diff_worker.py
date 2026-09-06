"""Periodic refresh of watched document snapshots and diffs."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.database import async_session_factory
from app.services.live_doc_diff import scan_all_users

logger = logging.getLogger(__name__)


async def run(stop_event: asyncio.Event) -> None:
    logger.info("live doc diff watcher started")
    interval = max(5.0, settings.live_doc_diff_interval_seconds)
    first_delay = min(5.0, interval)

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=first_delay)
        return
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        try:
            async with async_session_factory() as session:
                written = await scan_all_users(session)
            if written:
                logger.info("Live doc diff watcher wrote %s event(s)", written)
        except Exception:
            logger.exception("Live doc diff watcher pass failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            break
        except asyncio.TimeoutError:
            continue

    logger.info("live doc diff watcher stopped")
