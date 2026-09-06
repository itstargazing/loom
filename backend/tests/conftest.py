"""Test fixtures.

These tests cover pure logic only — schemas, prompts, and the classification
retry loop — so they run with no Postgres or Redis. Settings are pinned here so
a developer's local ``.env`` cannot change the outcome.
"""

import os
from datetime import UTC, datetime
from uuid import uuid4

os.environ.setdefault("AI_PROVIDER", "stub")
os.environ.setdefault("AI_API_KEY", "")

import pytest  # noqa: E402

from app.schemas.capture import CaptureEventIn  # noqa: E402
from app.services.classification import ClassifiableEvent  # noqa: E402


@pytest.fixture
def highlight_event() -> ClassifiableEvent:
    return ClassifiableEvent(
        event_type="highlight_selected",
        source_url="https://arxiv.org/abs/2401.00001",
        page_title="Attention Is All You Need",
        occurred_at="2026-08-28T10:00:00+00:00",
        payload={
            "text": "positional encoding",
            "context": (
                "Since our model contains no recurrence, we inject positional "
                "encoding to give the model information about token order."
            ),
        },
    )


@pytest.fixture
def make_capture_event():
    def _make(**overrides) -> CaptureEventIn:
        payload = {
            "id": str(uuid4()),
            "type": "text_copied",
            "sourceUrl": "https://example.com/article",
            "pageTitle": "An Article",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {"text": "some copied text"},
        }
        payload.update(overrides)
        return CaptureEventIn.model_validate(payload)

    return _make
