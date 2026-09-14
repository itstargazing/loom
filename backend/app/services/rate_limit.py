"""Distributed rate limits via Redis, with in-process fallback for tests/offline."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.redis import redis_client


class SlidingWindowLimiter:
    """In-process limiter used by unit tests and as Redis fallback."""

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
llm_limiter = SlidingWindowLimiter()
capture_limiter = SlidingWindowLimiter()

_REDIS_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
  return 0
end
redis.call('ZADD', key, now, member)
redis.call('PEXPIRE', key, math.floor(window * 1000) + 1000)
return 1
"""


async def _check(key: str, *, limit: int, window_seconds: float, memory: SlidingWindowLimiter) -> None:
    member = f"{time.time_ns()}"
    try:
        allowed = await redis_client.eval(
            _REDIS_SCRIPT,
            1,
            key,
            str(time.time()),
            str(window_seconds),
            str(limit),
            member,
        )
        if int(allowed) == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded: {limit} requests per "
                    f"{int(window_seconds)}s. Try again shortly."
                ),
            )
        return
    except HTTPException:
        raise
    except Exception:
        memory.check(key, limit=limit, window_seconds=window_seconds)


async def limit_classification(user_id: str) -> None:
    await _check(
        f"rl:classify:{user_id}",
        limit=settings.classification_rate_limit_per_minute,
        window_seconds=60.0,
        memory=classification_limiter,
    )


async def limit_llm(user_id: str) -> None:
    await _check(
        f"rl:llm:{user_id}",
        limit=settings.llm_rate_limit_per_minute,
        window_seconds=60.0,
        memory=llm_limiter,
    )


async def limit_capture(user_id: str) -> None:
    await _check(
        f"rl:capture:{user_id}",
        limit=settings.capture_rate_limit_per_minute,
        window_seconds=60.0,
        memory=capture_limiter,
    )
