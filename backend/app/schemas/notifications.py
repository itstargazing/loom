from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class NotificationOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    kind: str
    title: str
    body: str
    href: str | None = None
    read_at: datetime | None = None
    dismissed_at: datetime | None = None
    created_at: datetime


class NotificationListOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[NotificationOut]
    unread: int
