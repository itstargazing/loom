"""Structured output contract for event classification.

Shape notes, because they are load-bearing rather than stylistic:

* Every model sets ``extra="forbid"`` and gives no field defaults, so Pydantic
  emits ``additionalProperties: false`` and lists every property as required —
  the two things provider strict modes demand.
* Constraints such as bounds on ``confidence`` live in validators, not in
  ``Field(...)``, because ``minimum``/``maximum`` would appear in the JSON
  schema and be rejected. ``tests/test_classification_schema.py`` enforces this.
* Extracted fields are one flat, all-nullable object instead of a discriminated
  union per category. Pydantic renders unions as ``oneOf``, which strict mode
  does not accept; per-category requirements are checked server-side instead.
"""

from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

SkillCategory = Literal[
    "glossary_term",
    "citation",
    "deadline",
    "contradiction_candidate",
    "reading_highlight",
    "product_listing",
    "job_listing",
    "contract_clause",
    "none",
]

DeadlineKind = Literal[
    "assignment_due",
    "exam",
    "payment_due",
    "rsvp",
    "application_due",
    "other",
]

RiskLevel = Literal["low", "medium", "high"]

#  Fields that must be non-null for a classification in each category to be
#  usable. Enforced server-side since the schema cannot express it.
REQUIRED_FIELDS: dict[SkillCategory, tuple[str, ...]] = {
    "glossary_term": ("term", "definition"),
    "citation": ("quote",),
    "deadline": ("deadline_title", "deadline_date"),
    "contradiction_candidate": ("claim", "topic"),
    "reading_highlight": ("passage",),
    "product_listing": ("product_name",),
    "job_listing": ("job_title",),
    "contract_clause": ("clause_text", "flag_reason", "risk_level"),
    "none": (),
}


class SpecField(BaseModel):
    """A single product spec. A list of pairs, since strict mode forbids maps."""

    model_config = ConfigDict(extra="forbid")

    name: str
    value: str


class ExtractedFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # glossary_term
    term: str | None
    definition: str | None

    # citation
    quote: str | None
    author: str | None
    work_title: str | None
    publisher: str | None
    published_date: str | None

    # deadline
    deadline_title: str | None
    deadline_date: str | None
    deadline_kind: DeadlineKind | None

    # contradiction_candidate
    claim: str | None
    topic: str | None

    # reading_highlight
    passage: str | None
    reading_heading: str | None
    reading_dwell_ms: int | None

    # product_listing
    product_name: str | None
    price: str | None
    specs: list[SpecField] | None

    # job_listing
    job_title: str | None
    company: str | None
    salary: str | None
    requirements: list[str] | None
    application_deadline: str | None

    # contract_clause
    clause_text: str | None
    flag_reason: str | None
    risk_level: RiskLevel | None

    @classmethod
    def of(cls, **values: Any) -> "ExtractedFields":
        """Build with only the relevant fields set; the rest become null.

        Needed because the model intentionally has no defaults.
        """
        populated = {name: None for name in cls.model_fields}
        populated.update(values)
        return cls(**populated)

    def present(self) -> dict[str, Any]:
        """Only the fields the model actually filled in."""
        return {
            name: value
            for name, value in self.model_dump().items()
            if value is not None and value != []
        }


class ClassificationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SkillCategory
    #  0.0 to 1.0; clamped rather than range-constrained, see module docstring.
    confidence: float
    #  Short justification, surfaced in the dashboard for low-confidence items.
    reason: str
    fields: ExtractedFields

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, value: float) -> float:
        return min(1.0, max(0.0, value))

    @model_validator(mode="after")
    def _require_category_fields(self) -> Self:
        missing = [
            name
            for name in REQUIRED_FIELDS[self.category]
            if getattr(self.fields, name) in (None, "", [])
        ]
        if missing:
            raise ValueError(
                f"category '{self.category}' requires non-empty fields: {', '.join(missing)}"
            )
        return self


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #  One event may legitimately feed several skills, e.g. a highlighted
    #  sentence in a PDF that is both a glossary term and a reading highlight.
    classifications: list[ClassificationItem]

    @model_validator(mode="after")
    def _none_is_exclusive(self) -> Self:
        categories = [item.category for item in self.classifications]

        if "none" in categories and len(categories) > 1:
            raise ValueError("'none' cannot be combined with other categories")

        duplicates = {c for c in categories if categories.count(c) > 1}
        if duplicates:
            raise ValueError(f"duplicate categories: {', '.join(sorted(duplicates))}")

        return self

    @property
    def categories(self) -> list[str]:
        return [item.category for item in self.classifications]

    @property
    def is_none(self) -> bool:
        return self.categories == ["none"]


def classification_json_schema() -> dict[str, Any]:
    """The schema handed to the provider for strict structured output."""
    return ClassificationResult.model_json_schema()


ClassificationResultOut = Annotated[ClassificationResult, "validated classifier output"]
