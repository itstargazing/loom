import json
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.core.config import settings

CaptureEventType = Literal[
    "highlight_selected",
    "text_copied",
    "page_opened",
    "scroll_dwell",
    "upload_field_detected",
]


class CaptureEventIn(BaseModel):
    """One capture signal, in the camelCase wire format the extension emits."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    type: CaptureEventType
    source_url: Annotated[str, Field(max_length=2048)]
    page_title: Annotated[str, Field(default="", max_length=1024)]
    timestamp: datetime
    payload: dict[str, Any]

    @field_validator("payload")
    @classmethod
    def _reject_oversized_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        # Guards against a compromised or buggy extension shipping huge blobs.
        if len(json.dumps(value)) > settings.max_payload_chars:
            raise ValueError(
                f"payload exceeds {settings.max_payload_chars} characters"
            )
        return value


class CaptureBatchIn(BaseModel):
    events: Annotated[list[CaptureEventIn], Field(min_length=1)]


class CaptureBatchAck(BaseModel):
    """Returned immediately after queueing, before anything is persisted."""

    accepted: int
    queued: int


class CaptureEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)

    id: UUID
    event_type: str
    source_url: str
    page_title: str
    payload: dict[str, Any]
    occurred_at: datetime
    received_at: datetime
