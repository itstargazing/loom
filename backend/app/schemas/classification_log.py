"""Read models for logged classification outcomes.

Separate from ``schemas/classification.py`` because that module's shape is
constrained by provider strict-mode rules; these are ordinary API responses.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.classification import ClassificationResult


class EventClassificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    capture_event_id: uuid.UUID
    status: str
    provider: str
    model: str
    categories: list[str]
    result: ClassificationResult | None
    error: str | None
    attempts: int
    latency_ms: int
    created_at: datetime


class CategoryCount(BaseModel):
    category: str
    count: int


class ClassificationStats(BaseModel):
    total: int
    succeeded: int
    failed: int
    by_category: list[CategoryCount]
