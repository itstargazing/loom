"""Daily digest: last 24 hours of classified captures, with confirm/correct."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.models.breakthrough import ClassificationCorrection
from app.models.capture_event import CaptureEvent
from app.models.event_classification import EventClassification
from app.schemas.classification import (
    REQUIRED_FIELDS,
    ClassificationItem,
    ClassificationResult,
    ExtractedFields,
)
from app.services.classification_store import mark_routed
from app.services.skill_router import RoutingContext, route_classification

DIGEST_WINDOW = timedelta(hours=24)

CATEGORY_FIELD_HINTS: dict[str, str] = {
    "glossary_term": "This needs a term and definition to file as a glossary entry.",
    "citation": "This needs a quote to file as a citation.",
    "deadline": "This needs a title and date to file as a deadline.",
    "contradiction_candidate": "This needs a claim and topic to file as a contradiction.",
    "reading_highlight": "This needs a passage to file in the reading compiler.",
    "product_listing": "This needs a product name to file as a product.",
    "job_listing": "This needs a job title to file as a job listing.",
    "contract_clause": "This needs clause text, a flag reason, and a risk level.",
}


class DigestMissingFieldsError(ValueError):
    """Raised when a reassign is missing fields the target category requires."""

    def __init__(self, category: str, missing: list[str]):
        self.category = category
        self.missing = missing
        hint = CATEGORY_FIELD_HINTS.get(
            category,
            f"This category needs more detail: {', '.join(missing)}.",
        )
        super().__init__(hint)


def _camel_to_snake(name: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


def normalize_digest_fields(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Accept camelCase or snake_case keys from the digest UI."""
    if not raw:
        return {}
    allowed = set(ExtractedFields.model_fields)
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if value is None or value == "":
            continue
        snake = key if key in allowed else _camel_to_snake(key)
        if snake in allowed:
            out[snake] = value
    return out


def missing_required_fields(category: str, fields: dict[str, Any]) -> list[str]:
    if category not in REQUIRED_FIELDS:
        return []
    required = REQUIRED_FIELDS[category]  # type: ignore[index]
    return [
        name
        for name in required
        if fields.get(name) in (None, "", [])
    ]


def build_reassign_item(
    category: str,
    *,
    existing_fields: dict[str, Any],
    override_fields: dict[str, Any] | None,
) -> ClassificationItem:
    """Merge existing + provided fields and validate category requirements."""
    merged = {
        **normalize_digest_fields(existing_fields),
        **normalize_digest_fields(override_fields),
    }
    missing = missing_required_fields(category, merged)
    if missing:
        raise DigestMissingFieldsError(category, missing)
    return ClassificationItem(
        category=category,  # type: ignore[arg-type]
        confidence=1.0,
        reason="Reassigned in the daily digest.",
        fields=ExtractedFields.of(**{
            key: merged.get(key) for key in ExtractedFields.model_fields
        }),
    )

CATEGORY_GROUP_LABELS = {
    "glossary_term": "Glossary",
    "citation": "Citations",
    "deadline": "Deadlines",
    "contradiction_candidate": "Contradiction candidates",
    "reading_highlight": "Reading compiler",
    "product_listing": "Products",
    "job_listing": "Jobs",
    "contract_clause": "Contract flags",
    "none": "Unrouted",
    "pending": "Needs review",
}


def _primary_category(row: EventClassification) -> str:
    if row.review_status == "pending_review":
        return "pending"
    cats = [c for c in (row.categories or []) if c != "none"]
    return cats[0] if cats else "none"


def _item_fields(row: EventClassification) -> dict[str, Any]:
    result = row.result or {}
    items = result.get("classifications") or []
    if not items:
        return {}
    return items[0].get("fields") or {}


async def load_digest(session: AsyncSession, user_id: str) -> dict[str, Any]:
    since = datetime.now(UTC) - DIGEST_WINDOW
    result = await session.execute(
        select(EventClassification, CaptureEvent)
        .join(CaptureEvent, CaptureEvent.id == EventClassification.capture_event_id)
        .where(
            EventClassification.user_id == user_id,
            EventClassification.created_at >= since,
        )
        .order_by(EventClassification.created_at.desc())
    )
    groups: dict[str, list[dict[str, Any]]] = {}
    items: list[dict[str, Any]] = []
    for classification, event in result.all():
        group = _primary_category(classification)
        card = {
            "id": str(classification.id),
            "captureEventId": str(event.id),
            "snippet": classification.snippet or "",
            "sourceUrl": event.source_url,
            "pageTitle": event.page_title,
            "occurredAt": event.occurred_at,
            "categories": classification.categories,
            "confidence": classification.max_confidence,
            "reason": ((classification.result or {}).get("classifications") or [{}])[0].get(
                "reason"
            ),
            "reviewStatus": classification.review_status,
            "provider": classification.provider,
            "model": classification.model,
            "cached": classification.cached,
            "fields": _item_fields(classification),
            "group": group,
            "groupLabel": CATEGORY_GROUP_LABELS.get(group, group),
        }
        items.append(card)
        groups.setdefault(group, []).append(card)

    grouped = [
        {
            "key": key,
            "label": CATEGORY_GROUP_LABELS.get(key, key),
            "items": groups[key],
        }
        for key in (
            "pending",
            "glossary_term",
            "citation",
            "deadline",
            "contradiction_candidate",
            "reading_highlight",
            "product_listing",
            "job_listing",
            "contract_clause",
            "none",
        )
        if key in groups
    ]
    return {"since": since, "items": items, "groups": grouped}


async def apply_digest_action(
    session: AsyncSession,
    *,
    user_id: str,
    classification_id: uuid.UUID,
    action: str,
    category: str | None,
    fields: dict[str, Any] | None = None,
) -> EventClassification:
    result = await session.execute(
        select(EventClassification, CaptureEvent)
        .join(CaptureEvent, CaptureEvent.id == EventClassification.capture_event_id)
        .where(
            EventClassification.id == classification_id,
            EventClassification.user_id == user_id,
        )
    )
    row = result.first()
    if row is None:
        raise KeyError("classification")
    classification, event = row
    original = list(classification.categories or [])

    if action == "discard":
        classification.review_status = "discarded"
        classification.categories = ["none"]
        corrected = "none"
    elif action == "accept":
        classification.review_status = "accepted"
        corrected = original[0] if original else "none"
        await _route_now(session, classification, event)
        await mark_routed(session, event.id)
    elif action == "reassign":
        if not category:
            raise ValueError("reassign requires a category")
        item = build_reassign_item(
            category,
            existing_fields=_item_fields(classification),
            override_fields=fields,
        )
        classification.review_status = "reassigned"
        classification.categories = [category]
        classification.result = ClassificationResult(classifications=[item]).model_dump()
        corrected = category
        try:
            await _route_now(session, classification, event)
            await mark_routed(session, event.id)
        except Exception:
            logger.exception("Digest reassign routing failed for %s", classification.id)
            raise ValueError(
                "Could not file this into the skill store. Check the fields and try again."
            ) from None
    else:
        raise ValueError("unknown action")

    session.add(
        ClassificationCorrection(
            user_id=user_id,
            capture_event_id=event.id,
            original_categories=original,
            corrected_category=corrected,
            action=action,
            snippet=classification.snippet,
        )
    )
    await session.commit()
    await session.refresh(classification)
    return classification


async def _route_now(
    session: AsyncSession,
    classification: EventClassification,
    event: CaptureEvent,
) -> None:
    if not classification.result:
        return
    parsed = ClassificationResult.model_validate(classification.result)
    threshold = settings.classification_auto_route_min_confidence
    # Human accepted or reassigned: route even if original confidence was low.
    _ = threshold
    context = RoutingContext(
        user_id=classification.user_id,
        capture_event_id=event.id,
        source_url=event.source_url,
        page_title=event.page_title,
        context_text=str((event.payload or {}).get("context") or ""),
        occurred_at=event.occurred_at.isoformat(),
    )
    await route_classification(session, parsed, context)
