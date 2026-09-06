"""Tiny in-process rate limiter for expensive AI endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

from app.core.config import settings


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: float) -> None:
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded: {limit} requests per "
                    f"{int(window_seconds)}s. Try again shortly."
                ),
            )
        bucket.append(now)


classification_limiter = SlidingWindowLimiter()


def limit_classification(user_id: str) -> None:
    classification_limiter.check(
        f"classify:{user_id}",
        limit=settings.classification_rate_limit_per_minute,
        window_seconds=60.0,
    )
