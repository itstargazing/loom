"""HTTP-level tests for the ingest endpoint.

Redis is replaced with an in-memory recorder so routing, auth, validation, and
the batch guard are exercised without any infrastructure. Everything below the
queue is covered by the unit tests instead.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.services import capture_queue

AUTH = {"Authorization": f"Bearer {settings.stub_auth_token}"}


@pytest.fixture
def queued(monkeypatch) -> list[dict[str, str]]:
    """Captures what would have been published to Redis."""
    published: list[dict[str, str]] = []

    async def fake_publish_many(entries: list[dict[str, str]]) -> int:
        published.extend(entries)
        return len(entries)

    monkeypatch.setattr(
        capture_queue.capture_stream, "publish_many", fake_publish_many
    )
    return published


@pytest.fixture
async def client() -> AsyncClient:
    # No lifespan, so the app never reaches out to Redis or Postgres on startup.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client


def _event(**overrides) -> dict:
    event = {
        "id": str(uuid4()),
        "type": "highlight_selected",
        "sourceUrl": "https://example.com/article",
        "pageTitle": "An Article",
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": {"text": "something highlighted", "context": "surrounding text"},
    }
    event.update(overrides)
    return event


async def test_ingest_accepts_a_batch(client, queued):
    response = await client.post(
        "/api/capture/events", json={"events": [_event(), _event()]}, headers=AUTH
    )

    assert response.status_code == 202
    assert response.json() == {"accepted": 2, "queued": 2}
    assert len(queued) == 2
    assert queued[0]["user_id"] == settings.stub_user_id


async def test_queued_entry_carries_the_camel_case_event(client, queued):
    await client.post("/api/capture/events", json={"events": [_event()]}, headers=AUTH)

    assert "sourceUrl" in queued[0]["event"]


async def test_missing_token_is_rejected(client, queued):
    response = await client.post("/api/capture/events", json={"events": [_event()]})

    assert response.status_code == 403
    assert queued == []


async def test_wrong_token_is_rejected(client, queued):
    response = await client.post(
        "/api/capture/events",
        json={"events": [_event()]},
        headers={"Authorization": "Bearer nope"},
    )

    assert response.status_code == 401
    assert queued == []


async def test_empty_batch_is_rejected(client, queued):
    response = await client.post("/api/capture/events", json={"events": []}, headers=AUTH)

    assert response.status_code == 422
    assert queued == []


async def test_invalid_event_type_is_rejected(client, queued):
    response = await client.post(
        "/api/capture/events", json={"events": [_event(type="telepathy")]}, headers=AUTH
    )

    assert response.status_code == 422
    assert queued == []


async def test_oversized_batch_is_rejected(client, queued):
    events = [_event() for _ in range(settings.max_events_per_batch + 1)]
    response = await client.post(
        "/api/capture/events", json={"events": events}, headers=AUTH
    )

    assert response.status_code == 413
    assert queued == []


async def test_health_needs_no_auth(client):
    assert (await client.get("/health")).status_code == 200
