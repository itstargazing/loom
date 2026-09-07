from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BriefOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    topic: str
    markdown: str
    source_event_ids: list[str]
    deadline_id: str | None = None
    created_at: datetime


class BriefRequestIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    topic: str | None = None
    deadline_id: str | None = None
