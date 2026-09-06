"""Queue of persisted capture events awaiting classification.

Kept separate from the capture stream so ingest stays fast and classification —
which is slow, costs money, and fails differently — retries on its own terms.
"""

from uuid import UUID

from app.core.config import settings
from app.core.streams import RedisStream

classification_stream = RedisStream(
    name="loom:classify:events",
    group="loom-classification-workers",
    max_len=settings.capture_stream_max_len,
)


async def enqueue_for_classification(pairs: list[tuple[str, UUID]]) -> int:
    """Queue (user_id, capture_event_id) pairs. Returns the number queued."""
    return await classification_stream.publish_many(
        [{"user_id": user_id, "capture_event_id": str(event_id)} for user_id, event_id in pairs]
    )


def parse_entry(fields: dict[str, str]) -> tuple[str, UUID]:
    """Raises if malformed, so the worker can drop poison entries."""
    return fields["user_id"], UUID(fields["capture_event_id"])
