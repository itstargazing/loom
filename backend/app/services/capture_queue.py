"""Queue of raw capture events awaiting persistence.

The ingest endpoint only writes here, so a request is acknowledged as soon as
the events are durably queued rather than after a database write.
"""

import json

from app.core.config import settings
from app.core.streams import RedisStream
from app.schemas.capture import CaptureEventIn

capture_stream = RedisStream(
    name="loom:capture:events",
    group="loom-capture-workers",
    max_len=settings.capture_stream_max_len,
)


async def enqueue_capture_events(user_id: str, events: list[CaptureEventIn]) -> int:
    """Queue events for asynchronous persistence. Returns the number queued."""
    return await capture_stream.publish_many(
        [
            {
                "user_id": user_id,
                # by_alias keeps the camelCase wire format all the way through,
                # so what the worker validates is what the extension sent.
                "event": event.model_dump_json(by_alias=True),
            }
            for event in events
        ]
    )


def parse_entry(fields: dict[str, str]) -> tuple[str, CaptureEventIn]:
    """Split a stream entry back into its user id and a validated event.

    Raises if the entry is malformed, so the worker can drop poison entries
    instead of retrying them forever.
    """
    return fields["user_id"], CaptureEventIn.model_validate(json.loads(fields["event"]))
