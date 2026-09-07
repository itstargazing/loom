"""Periodic deadline nudge scanner."""

from __future__ import annotations

import asyncio
import logging

from app.core.database import async_session_factory
from app.services.nudges import scan_nudges

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 15 * 60


async def run(stop_event: asyncio.Event) -> None:
    logger.info("nudge worker started")
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=20.0)
        return
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        try:
            async with async_session_factory() as session:
                written = await scan_nudges(session)
            if written:
                logger.info("Posted %s deadline nudge(s)", written)
        except Exception:
            logger.exception("Nudge pass failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=INTERVAL_SECONDS)
            return
        except asyncio.TimeoutError:
            continue
