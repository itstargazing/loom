"""Request/response models for the Multi-Doc Live Diff skill."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class WatchedDocumentOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    set_id: uuid.UUID
    label: str
    source_url: str
    created_at: datetime
    latest_snapshot_at: datetime | None = None
    snapshot_count: int = 0


class DocumentDiffEventOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    set_id: uuid.UUID
    left_document_id: uuid.UUID
    right_document_id: uuid.UUID
    left_label: str
    right_label: str
    unified_diff: str
    change_summary: str
    is_meaningful: bool
    detected_at: datetime
    viewed_at: datetime | None


class WatchedSetOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    name: str
    created_at: datetime
    last_viewed_at: datetime | None
    documents: list[WatchedDocumentOut] = Field(default_factory=list)
    unread_meaningful: int = 0
    latest_event_at: datetime | None = None


class WatchedSetDetailOut(WatchedSetOut):
    events: list[DocumentDiffEventOut] = Field(default_factory=list)


class WatchedSetIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str

    @model_validator(mode="after")
    def _name_required(self) -> "WatchedSetIn":
        if not self.name.strip():
            raise ValueError("Name cannot be empty")
        self.name = self.name.strip()
        return self


class WatchedDocumentIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    source_url: str
    label: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def _url_required(self) -> "WatchedDocumentIn":
        if not self.source_url.strip():
            raise ValueError("sourceUrl cannot be empty")
        self.source_url = self.source_url.strip()
        if self.label is not None:
            self.label = self.label.strip() or None
        return self


class SnapshotIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    text: str

    @model_validator(mode="after")
    def _text_required(self) -> "SnapshotIn":
        if not self.text.strip():
            raise ValueError("text cannot be empty")
        return self


class UnreadCountOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    unread_meaningful: int
