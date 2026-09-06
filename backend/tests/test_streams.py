"""Stale-claim fallback when Redis is older than 6.2 (no XAUTOCLAIM)."""

from redis.exceptions import ResponseError

from app.core.streams import RedisStream


class FakeRedis:
    def __init__(self, *, autoclaim_ok: bool, pending=None, claimed=None):
        self.autoclaim_ok = autoclaim_ok
        self.pending = pending or []
        self.claimed = claimed or []
        self.calls: list[str] = []

    async def xautoclaim(self, **kwargs):
        self.calls.append("xautoclaim")
        if not self.autoclaim_ok:
            raise ResponseError("unknown command `XAUTOCLAIM`")
        return ["0-0", self.claimed]

    async def xpending_range(self, **kwargs):
        self.calls.append("xpending_range")
        return self.pending

    async def xclaim(self, **kwargs):
        self.calls.append("xclaim")
        return self.claimed


async def test_claim_stale_uses_xautoclaim_when_available(monkeypatch):
    fake = FakeRedis(autoclaim_ok=True, claimed=[("1-0", {"k": "v"})])
    monkeypatch.setattr("app.core.streams.redis_client", fake)
    stream = RedisStream("loom:test", "g", 100)

    entries = await stream.claim_stale("c1", min_idle_ms=1000, count=10)

    assert entries == [("1-0", {"k": "v"})]
    assert fake.calls == ["xautoclaim"]


async def test_claim_stale_falls_back_to_xclaim_on_old_redis(monkeypatch):
    fake = FakeRedis(
        autoclaim_ok=False,
        pending=[{"message_id": "1-0", "time_since_delivered": 90_000}],
        claimed=[("1-0", {"k": "v"})],
    )
    monkeypatch.setattr("app.core.streams.redis_client", fake)
    stream = RedisStream("loom:test", "g", 100)

    entries = await stream.claim_stale("c1", min_idle_ms=60_000, count=10)

    assert entries == [("1-0", {"k": "v"})]
    assert fake.calls == ["xautoclaim", "xpending_range", "xclaim"]


async def test_claim_stale_skips_entries_that_are_not_idle_enough(monkeypatch):
    fake = FakeRedis(
        autoclaim_ok=False,
        pending=[{"message_id": "1-0", "time_since_delivered": 100}],
    )
    monkeypatch.setattr("app.core.streams.redis_client", fake)
    stream = RedisStream("loom:test", "g", 100)

    entries = await stream.claim_stale("c1", min_idle_ms=60_000, count=10)

    assert entries == []
    assert fake.calls == ["xautoclaim", "xpending_range"]
