from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TrailNodeOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    capture_event_id: str
    snippet: str
    source_url: str
    page_title: str
    referring_url: str | None = None
    occurred_at: datetime
    categories: list[str]
    review_status: str | None = None


class TrailEdgeOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    source: str
    target: str
    kind: str


class TrailOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    nodes: list[TrailNodeOut]
    edges: list[TrailEdgeOut]
    session_started_at: datetime | None = None
    extras: dict[str, Any] = {}
