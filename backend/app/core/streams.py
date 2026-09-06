"""Thin wrapper around a Redis Stream consumed by a worker group.

Streams are used rather than plain lists because they give per-entry
acknowledgement plus redelivery of entries a crashed worker never finished.
Every background job in LOOM shares this primitive.
"""

import logging

from redis.exceptions import ResponseError

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

#  (entry_id, fields) as returned by redis-py.
StreamEntry = tuple[str, dict[str, str]]


class RedisStream:
    def __init__(self, name: str, group: str, max_len: int) -> None:
        self.name = name
        self.group = group
        self.max_len = max_len

    async def ensure_group(self) -> None:
        """Create the stream and consumer group if they do not exist yet."""
        try:
            await redis_client.xgroup_create(self.name, self.group, id="0", mkstream=True)
            logger.info("Created consumer group %s on %s", self.group, self.name)
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    async def publish_many(self, entries: list[dict[str, str]]) -> int:
        """Append entries in a single round trip. Returns the number published."""
        if not entries:
            return 0

        pipeline = redis_client.pipeline()
        for fields in entries:
            pipeline.xadd(self.name, fields, maxlen=self.max_len, approximate=True)
        await pipeline.execute()

        return len(entries)

    async def read_new(self, consumer: str, count: int, block_ms: int) -> list[StreamEntry]:
        """Block briefly for entries not yet delivered to anyone."""
        response = await redis_client.xreadgroup(
            groupname=self.group,
            consumername=consumer,
            streams={self.name: ">"},
            count=count,
            block=block_ms,
        )
        return response[0][1] if response else []

    async def claim_stale(
        self, consumer: str, min_idle_ms: int, count: int
    ) -> list[StreamEntry]:
        """Take over entries another worker fetched but never acknowledged."""
        try:
            result = await redis_client.xautoclaim(
                name=self.name,
                groupname=self.group,
                consumername=consumer,
                min_idle_time=min_idle_ms,
                count=count,
            )
        except ResponseError as error:
            # XAUTOCLAIM arrived in Redis 6.2. Older servers (including the
            # common Windows 5.x port) still have streams and XCLAIM.
            if "unknown command" not in str(error).lower():
                raise
            return await self._claim_stale_via_xpending(
                consumer, min_idle_ms, count
            )
        # Redis 7 returns (cursor, entries, deleted); Redis 6.2 omits the last item.
        return result[1]

    async def _claim_stale_via_xpending(
        self, consumer: str, min_idle_ms: int, count: int
    ) -> list[StreamEntry]:
        pending = await redis_client.xpending_range(
            name=self.name,
            groupname=self.group,
            min="-",
            max="+",
            count=count,
        )
        stale_ids = [
            item["message_id"]
            for item in pending or []
            if int(item.get("time_since_delivered") or 0) >= min_idle_ms
        ]
        if not stale_ids:
            return []
        claimed = await redis_client.xclaim(
            name=self.name,
            groupname=self.group,
            consumername=consumer,
            min_idle_time=min_idle_ms,
            message_ids=stale_ids,
        )
        return list(claimed or [])

    async def ack(self, entry_ids: list[str]) -> None:
        if entry_ids:
            await redis_client.xack(self.name, self.group, *entry_ids)
