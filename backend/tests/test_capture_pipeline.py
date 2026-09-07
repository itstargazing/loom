"""The capture wire format and the queue round-trip that carries it.

The extension speaks camelCase and the database speaks snake_case. A mismatch
here breaks ingest silently in the worker rather than at the API boundary, so
the serialize/deserialize hop is asserted directly.
"""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.capture import CaptureBatchIn, CaptureEventIn
from app.services.capture_ingest import _to_row
from app.services.capture_queue import parse_entry as parse_capture_entry
from app.services.classification_queue import parse_entry as parse_classification_entry


def test_camel_case_wire_format_is_accepted(make_capture_event):
    event = make_capture_event(
        sourceUrl="https://example.com/x", pageTitle="Title", type="highlight_selected"
    )

    assert event.source_url == "https://example.com/x"
    assert event.page_title == "Title"
    assert event.type == "highlight_selected"


def test_page_title_defaults_to_empty():
    event = CaptureEventIn.model_validate(
        {
            "id": str(uuid4()),
            "type": "page_opened",
            "sourceUrl": "https://example.com",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {},
        }
    )
    assert event.page_title == ""


def test_unknown_event_type_is_rejected(make_capture_event):
    with pytest.raises(ValidationError):
        make_capture_event(type="mind_read")


def test_oversized_payload_is_rejected(make_capture_event):
    with pytest.raises(ValidationError, match="exceeds"):
        make_capture_event(payload={"text": "x" * (settings.max_payload_chars + 100)})


def test_batch_requires_at_least_one_event():
    with pytest.raises(ValidationError):
        CaptureBatchIn(events=[])


def test_queue_round_trip_preserves_every_field(make_capture_event):
    """What the worker validates must equal what the endpoint queued."""
    event = make_capture_event(type="scroll_dwell", pageTitle="Long Read")

    # Mirrors enqueue_capture_events without needing a live Redis.
    serialized = {"user_id": "dev-user", "event": event.model_dump_json(by_alias=True)}
    user_id, restored = parse_capture_entry(serialized)

    assert user_id == "dev-user"
    assert restored == event


def test_queue_payload_uses_camel_case_on_the_wire(make_capture_event):
    event = make_capture_event()
    encoded = json.loads(event.model_dump_json(by_alias=True))

    assert "sourceUrl" in encoded
    assert "source_url" not in encoded


def test_malformed_queue_entry_raises(make_capture_event):
    with pytest.raises(Exception):
        parse_capture_entry({"user_id": "dev-user", "event": "{not json"})

    with pytest.raises(KeyError):
        parse_capture_entry({"event": make_capture_event().model_dump_json()})


def test_to_row_maps_wire_names_to_columns(make_capture_event):
    event = make_capture_event(type="upload_field_detected")
    row = _to_row("dev-user", event)

    assert row == {
        "id": event.id,
        "user_id": "dev-user",
        "event_type": "upload_field_detected",
        "source_url": event.source_url,
        "page_title": event.page_title,
        "payload": event.payload,
        "occurred_at": event.timestamp,
        "referring_url": None,
    }


def test_classification_queue_round_trip():
    event_id = uuid4()
    user_id, restored = parse_classification_entry(
        {"user_id": "dev-user", "capture_event_id": str(event_id)}
    )

    assert user_id == "dev-user"
    assert restored == event_id
    assert isinstance(restored, UUID)


def test_classification_queue_rejects_a_bad_uuid():
    with pytest.raises(ValueError):
        parse_classification_entry({"user_id": "dev-user", "capture_event_id": "nope"})
