"""API models for the batch PDF form filler."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class FormProfileOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    name: str
    values: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FormProfileIn(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    values: dict[str, Any] = Field(default_factory=dict)


class FormProfilePatch(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str | None = None
    values: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "FormProfilePatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class FormFieldOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    type: str
    value: str | None = None
    options: list[str] = Field(default_factory=list)


class FormDocumentOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    filename: str
    source_url: str
    fields: list[FormFieldOut]
    field_count: int
    created_at: datetime


class FieldMatchOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    field_name: str
    field_type: str
    profile_key: str | None
    value: str | None
    confidence: float
    needs_manual: bool
    reason: str


class DocumentMatchOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    document_id: uuid.UUID
    filename: str
    matches: list[FieldMatchOut]
    auto_filled: int
    needs_manual: int


class MatchRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    profile_id: uuid.UUID
    document_ids: list[uuid.UUID]


class FillOverride(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    field_name: str
    value: str


class DocumentFillOverrides(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    document_id: uuid.UUID
    overrides: list[FillOverride] = Field(default_factory=list)


class FillRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    profile_id: uuid.UUID
    document_ids: list[uuid.UUID]
    documents: list[DocumentFillOverrides] = Field(default_factory=list)
