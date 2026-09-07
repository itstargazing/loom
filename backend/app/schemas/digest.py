from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class DigestCardOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    capture_event_id: str
    snippet: str
    source_url: str
    page_title: str
    occurred_at: datetime
    categories: list[str]
    confidence: float
    reason: str | None = None
    review_status: str
    provider: str
    model: str
    cached: bool
    fields: dict[str, Any]
    group: str
    group_label: str


class DigestGroupOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    key: str
    label: str
    items: list[DigestCardOut]


class DigestOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    since: datetime
    items: list[DigestCardOut]
    groups: list[DigestGroupOut]


class DigestActionIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    action: str = Field(pattern="^(accept|reassign|discard)$")
    category: str | None = None
