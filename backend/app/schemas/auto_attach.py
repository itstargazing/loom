"""Schemas for Smart File Auto-Attach."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class RecentDocumentOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    filename: str
    source_url: str
    doc_type: str
    summary: str
    mime_type: str
    has_file: bool = False
    created_at: datetime
    last_seen_at: datetime


class RecentDocumentIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    filename: str
    source_url: str = ""
    doc_type: str | None = None
    summary: str = ""
    mime_type: str = ""

    @model_validator(mode="after")
    def _filename_required(self) -> "RecentDocumentIn":
        if not self.filename.strip():
            raise ValueError("filename cannot be empty")
        self.filename = self.filename.strip()
        self.source_url = (self.source_url or "").strip()
        self.summary = (self.summary or "").strip()
        self.mime_type = (self.mime_type or "").strip()
        if self.doc_type is not None:
            self.doc_type = self.doc_type.strip() or None
        return self


class AutoAttachMatchRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    label_text: str = ""
    surrounding_text: str = ""
    field_name: str | None = None
    accept: str | None = None


class AutoAttachMatchOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    document_id: uuid.UUID
    filename: str
    doc_type: str
    source_url: str
    summary: str
    has_file: bool
    confidence: float
    reason: str


class AutoAttachMatchResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    match: AutoAttachMatchOut | None = None
    candidates: list[AutoAttachMatchOut] = Field(default_factory=list)
