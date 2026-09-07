"""Redis cache for classification results of identical / near-identical captures."""

from __future__ import annotations

import hashlib
import json
import logging

from app.core.redis import redis_client
from app.schemas.classification import ClassificationResult
from app.services.capture_text import normalize_snippet

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


def cache_key(*, user_id: str, event_type: str, snippet: str) -> str:
    normalized = normalize_snippet(snippet)
    digest = hashlib.sha256(f"{user_id}\0{event_type}\0{normalized}".encode("utf-8")).hexdigest()
    return f"loom:classify:{digest}"


async def get_cached_result(key: str) -> ClassificationResult | None:
    try:
        raw = await redis_client.get(key)
    except Exception:
        logger.debug("Classification cache read failed", exc_info=True)
        return None
    if not raw:
        return None
    try:
        return ClassificationResult.model_validate(json.loads(raw))
    except Exception:
        logger.warning("Dropped unreadable classification cache entry")
        return None


async def set_cached_result(key: str, result: ClassificationResult) -> None:
    try:
        await redis_client.set(key, result.model_dump_json(), ex=CACHE_TTL_SECONDS)
    except Exception:
        logger.debug("Classification cache write failed", exc_info=True)
