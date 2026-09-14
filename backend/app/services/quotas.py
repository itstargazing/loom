"""Daily plan quotas backed by Redis (free vs pro)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.models.account import UserAccount


def _day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


async def _plan_for(user_id: str) -> str:
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(UserAccount.plan).where(UserAccount.user_id == user_id)
            )
            plan = result.scalar_one_or_none()
            return (plan or "free").strip().lower()
    except Exception:
        return "free"


def _limits(plan: str) -> tuple[int, int]:
    if plan == "pro":
        return settings.pro_events_per_day, settings.pro_ask_per_day
    return settings.free_events_per_day, settings.free_ask_per_day


async def _incr(key: str, amount: int, limit: int) -> int:
    try:
        pipe = redis_client.pipeline()
        pipe.incrby(key, amount)
        pipe.expire(key, 60 * 60 * 36)
        count, _ = await pipe.execute()
        count = int(count)
        if count > limit:
            # Best-effort rollback so a burst does not permanently consume quota.
            await redis_client.decrby(key, amount)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Daily quota exceeded ({limit}). Upgrade to Pro or try again tomorrow."
                ),
            )
        return count
    except HTTPException:
        raise
    except Exception:
        # Fail open on Redis outage so capture is not wedged offline.
        return 0


async def assert_capture_quota(user_id: str, event_count: int) -> None:
    plan = await _plan_for(user_id)
    events_limit, _ = _limits(plan)
    await _incr(f"quota:events:{user_id}:{_day_key()}", event_count, events_limit)


async def assert_ask_quota(user_id: str) -> None:
    plan = await _plan_for(user_id)
    _, ask_limit = _limits(plan)
    await _incr(f"quota:ask:{user_id}:{_day_key()}", 1, ask_limit)


async def quota_status(user_id: str, session: AsyncSession | None = None) -> dict:
    plan = "free"
    if session is not None:
        result = await session.execute(
            select(UserAccount).where(UserAccount.user_id == user_id)
        )
        account = result.scalar_one_or_none()
        if account is not None:
            plan = (account.plan or "free").strip().lower()
    else:
        plan = await _plan_for(user_id)

    events_limit, ask_limit = _limits(plan)
    day = _day_key()
    try:
        events_used = int(await redis_client.get(f"quota:events:{user_id}:{day}") or 0)
        ask_used = int(await redis_client.get(f"quota:ask:{user_id}:{day}") or 0)
    except Exception:
        events_used = 0
        ask_used = 0

    return {
        "plan": plan,
        "eventsPerDay": events_limit,
        "eventsUsedToday": events_used,
        "askPerDay": ask_limit,
        "askUsedToday": ask_used,
    }
