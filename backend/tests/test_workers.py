"""Worker batch handling: acknowledgement, poison entries, and hand-off.

Postgres and Redis are replaced with recorders. What matters here is *which*
entries get acknowledged and which events get passed downstream, since a mistake
either drops data silently or redelivers it forever.
"""

from uuid import uuid4

import pytest

from app.worker import capture_worker, classification_worker


@pytest.fixture
def capture_fakes(monkeypatch):
    """Stand in for the database and the classification queue."""
    recorded: dict[str, list] = {"acked": [], "queued": [], "persisted": []}

    async def fake_persist(session, entries):
        recorded["persisted"].append(entries)
        # Mimic ON CONFLICT DO NOTHING: only the first event in a batch is new.
        return [(user_id, event.id) for user_id, event in entries[:1]]

    async def fake_enqueue(pairs):
        recorded["queued"].extend(pairs)
        return len(pairs)

    async def fake_ack(entry_ids):
        recorded["acked"].extend(entry_ids)

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

    monkeypatch.setattr(capture_worker, "persist_capture_events", fake_persist)
    monkeypatch.setattr(capture_worker, "enqueue_for_classification", fake_enqueue)
    monkeypatch.setattr(capture_worker, "async_session_factory", FakeSession)
    monkeypatch.setattr(capture_worker.capture_stream, "ack", fake_ack)
    return recorded


def _entry(entry_id: str, event) -> tuple[str, dict[str, str]]:
    return entry_id, {
        "user_id": "dev-user",
        "event": event.model_dump_json(by_alias=True),
    }


async def test_valid_batch_is_persisted_and_acknowledged(
    capture_fakes, make_capture_event
):
    entries = [_entry("1-0", make_capture_event()), _entry("1-1", make_capture_event())]

    await capture_worker.handle(entries)

    assert sorted(capture_fakes["acked"]) == ["1-0", "1-1"]
    assert len(capture_fakes["persisted"][0]) == 2


async def test_only_newly_inserted_events_are_queued_for_classification(
    capture_fakes, make_capture_event
):
    """Redelivered events must not be classified again; each call costs money."""
    first = make_capture_event()
    entries = [_entry("1-0", first), _entry("1-1", make_capture_event())]

    await capture_worker.handle(entries)

    assert capture_fakes["queued"] == [("dev-user", first.id)]


async def test_malformed_entry_is_dropped_not_redelivered(
    capture_fakes, make_capture_event
):
    good = make_capture_event()
    entries = [("1-0", {"user_id": "dev-user", "event": "{broken"}), _entry("1-1", good)]

    await capture_worker.handle(entries)

    # Both acknowledged: the poison entry is dropped rather than retried forever.
    assert sorted(capture_fakes["acked"]) == ["1-0", "1-1"]
    assert len(capture_fakes["persisted"][0]) == 1


async def test_all_malformed_batch_acknowledges_without_persisting(capture_fakes):
    entries = [("1-0", {"user_id": "dev-user", "event": "{broken"})]

    await capture_worker.handle(entries)

    assert capture_fakes["acked"] == ["1-0"]
    assert capture_fakes["persisted"] == []
    assert capture_fakes["queued"] == []


@pytest.fixture
def classification_fakes(monkeypatch):
    recorded: dict[str, list] = {"acked": [], "classified": []}

    async def fake_ack(entry_ids):
        recorded["acked"].extend(entry_ids)

    monkeypatch.setattr(classification_worker.classification_stream, "ack", fake_ack)
    return recorded


async def test_successful_classification_is_acknowledged(
    classification_fakes, monkeypatch
):
    async def fake_classify_one(capture_event_id, queued_user_id):
        classification_fakes["classified"].append(capture_event_id)
        return True

    monkeypatch.setattr(classification_worker, "classify_and_route", fake_classify_one)

    event_id = uuid4()
    await classification_worker.handle(
        [("1-0", {"user_id": "dev-user", "capture_event_id": str(event_id)})]
    )

    assert classification_fakes["acked"] == ["1-0"]
    assert classification_fakes["classified"] == [event_id]


async def test_failed_classification_stays_pending(classification_fakes, monkeypatch):
    """An unacknowledged entry is what lets a provider outage be retried."""

    async def fake_classify_one(capture_event_id, queued_user_id):
        return False

    monkeypatch.setattr(classification_worker, "classify_and_route", fake_classify_one)

    await classification_worker.handle(
        [("1-0", {"user_id": "dev-user", "capture_event_id": str(uuid4())})]
    )

    assert classification_fakes["acked"] == []


async def test_unexpected_error_leaves_entry_pending(classification_fakes, monkeypatch):
    async def fake_classify_one(capture_event_id, queued_user_id):
        raise RuntimeError("database is on fire")

    monkeypatch.setattr(classification_worker, "classify_and_route", fake_classify_one)

    # Must not propagate, or one bad entry kills the whole worker loop.
    await classification_worker.handle(
        [("1-0", {"user_id": "dev-user", "capture_event_id": str(uuid4())})]
    )

    assert classification_fakes["acked"] == []


async def test_malformed_classification_entry_is_dropped(classification_fakes):
    await classification_worker.handle(
        [("1-0", {"user_id": "dev-user", "capture_event_id": "not-a-uuid"})]
    )

    assert classification_fakes["acked"] == ["1-0"]


async def test_one_bad_entry_does_not_block_the_rest(
    classification_fakes, monkeypatch
):
    async def fake_classify_one(capture_event_id, queued_user_id):
        return True

    monkeypatch.setattr(classification_worker, "classify_and_route", fake_classify_one)

    await classification_worker.handle(
        [
            ("1-0", {"user_id": "dev-user", "capture_event_id": "not-a-uuid"}),
            ("1-1", {"user_id": "dev-user", "capture_event_id": str(uuid4())}),
        ]
    )

    assert sorted(classification_fakes["acked"]) == ["1-0", "1-1"]
