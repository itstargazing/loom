"""Read models for the typed skill stores."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel


class SkillEntryBase(BaseModel):
    """The envelope every skill entry shares."""

    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    capture_event_id: uuid.UUID | None
    collection_id: uuid.UUID | None
    source_url: str
    page_title: str
    confidence: float
    times_seen: int
    occurrences: list[dict[str, Any]]
    created_at: datetime
    last_seen_at: datetime


class GlossaryTermOut(SkillEntryBase):
    term: str
    definition: str
    context_snippet: str


class CitationOut(SkillEntryBase):
    quote: str
    author: str | None
    work_title: str | None
    publisher: str | None
    published_date: str | None
    formatted: dict[str, str]


class DeadlineOut(SkillEntryBase):
    title: str
    due_text: str
    due_date: datetime | None
    kind: str | None
    context_snippet: str
    confirmed: bool


class ContradictionClaimOut(SkillEntryBase):
    claim: str
    topic: str


class ContradictionOut(BaseModel):
    """A flagged conflicting pair written by the contradiction watcher."""

    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    topic: str
    claim_a: str
    claim_b: str
    source_a_url: str
    source_b_url: str
    explanation: str
    dismissed: bool
    claim_a_id: uuid.UUID | None
    claim_b_id: uuid.UUID | None
    created_at: datetime


class ContradictionPatch(BaseModel):
    """Dismiss (or restore) a flagged contradiction."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dismissed: bool

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "ContradictionPatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class ReadingCompilerEntryOut(SkillEntryBase):
    passage: str
    dwell_ms: int
    heading: str | None


class ReadingCompilerEntryPatch(BaseModel):
    """File a reading passage or correct its heading."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    heading: str | None = None
    collection_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "ReadingCompilerEntryPatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class ReadingCompilePassageOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    passage: str
    heading: str | None
    source_url: str
    page_title: str
    dwell_ms: int
    last_seen_at: datetime


class ReadingCompileOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str
    markdown: str
    passages: list[ReadingCompilePassageOut]


class ProductListingOut(SkillEntryBase):
    name: str
    price: str | None
    specs: dict[str, str]


class JobListingOut(SkillEntryBase):
    title: str
    company: str | None
    salary: str | None
    requirements: list[str]
    application_deadline: str | None


class ContractFlagOut(SkillEntryBase):
    clause_text: str
    flag_reason: str
    risk_level: str


class SkillCount(BaseModel):
    skill: str
    label: str
    count: int


class CollectionIn(BaseModel):
    name: str
    description: str | None = None


class CollectionOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True, alias_generator=to_camel, populate_by_name=True
    )

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


class GlossaryTermPatch(BaseModel):
    """Partial update for a glossary entry. Omitted fields are left unchanged."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    term: str | None = None
    definition: str | None = None
    collection_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "GlossaryTermPatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class CitationPatch(BaseModel):
    """Correct bibliographic metadata; formatted APA/MLA strings are rebuilt."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    author: str | None = None
    work_title: str | None = None
    publisher: str | None = None
    published_date: str | None = None
    collection_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "CitationPatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class DeadlinePatch(BaseModel):
    """Confirm or correct a deadline. Omitted fields are left unchanged."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str | None = None
    due_text: str | None = None
    kind: str | None = None
    confirmed: bool | None = None
    collection_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "DeadlinePatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class ProductListingPatch(BaseModel):
    """Correct a listing's name, price, or specs."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str | None = None
    price: str | None = None
    specs: dict[str, str] | None = None
    collection_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "ProductListingPatch":
        if not self.model_fields_set:
            raise ValueError("No fields to update")
        return self


class NormalizedPriceOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    raw: str | None
    amount: float | None
    currency: str | None
    comparable: bool


class ProductCompareColumnOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: uuid.UUID
    name: str
    source_url: str
    page_title: str
    price: NormalizedPriceOut
    specs: dict[str, str]


class ProductCompareOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    columns: list[ProductCompareColumnOut]
    spec_keys: list[str]
    lowest_price_ids: list[uuid.UUID]
    price_note: str | None
