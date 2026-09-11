"""Digest reassign field validation and friendly error shaping."""

import pytest
from pydantic import ValidationError

from app.schemas.classification import ClassificationItem, ExtractedFields
from app.services.digest import (
    DigestMissingFieldsError,
    build_reassign_item,
    missing_required_fields,
    normalize_digest_fields,
)


def test_normalize_digest_fields_accepts_camel_and_snake():
    assert normalize_digest_fields(
        {"deadlineTitle": "Final paper", "deadline_date": "2026-12-12"}
    ) == {"deadline_title": "Final paper", "deadline_date": "2026-12-12"}


def test_missing_required_fields_for_deadline():
    assert missing_required_fields("deadline", {"deadline_title": "Paper"}) == [
        "deadline_date"
    ]
    assert missing_required_fields(
        "deadline",
        {"deadline_title": "Paper", "deadline_date": "2026-12-12"},
    ) == []


def test_reassign_to_deadline_without_fields_raises_friendly_error():
    with pytest.raises(DigestMissingFieldsError) as raised:
        build_reassign_item(
            "deadline",
            existing_fields={"passage": "Final paper due December 12, 2026"},
            override_fields=None,
        )
    assert raised.value.category == "deadline"
    assert "deadline_date" in raised.value.missing
    assert "deadline" in str(raised.value).lower()
    # Must not look like a raw Pydantic dump.
    assert "validation error" not in str(raised.value).lower()


def test_reassign_to_deadline_with_fields_builds_valid_item():
    item = build_reassign_item(
        "deadline",
        existing_fields={"passage": "ignored once overrides arrive"},
        override_fields={
            "deadlineTitle": "Final paper",
            "deadlineDate": "2026-12-12",
        },
    )
    assert item.category == "deadline"
    assert item.fields.deadline_title == "Final paper"
    assert item.fields.deadline_date == "2026-12-12"
    # Round-trip through ClassificationItem requirements.
    ClassificationItem.model_validate(item.model_dump())


def test_classification_item_still_rejects_incomplete_deadline():
    with pytest.raises(ValidationError):
        ClassificationItem(
            category="deadline",
            confidence=1.0,
            reason="test",
            fields=ExtractedFields.of(deadline_title="Only a title"),
        )


@pytest.mark.asyncio
async def test_digest_endpoint_returns_structured_missing_fields(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.core.config import settings
    from app.main import app
    from app.routers import digest as digest_router
    from app.services.digest import DigestMissingFieldsError

    async def boom(*_args, **_kwargs):
        raise DigestMissingFieldsError("deadline", ["deadline_title", "deadline_date"])

    monkeypatch.setattr(digest_router, "apply_digest_action", boom)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/digest/00000000-0000-0000-0000-000000000001",
            json={"action": "reassign", "category": "deadline"},
            headers={"Authorization": f"Bearer {settings.stub_auth_token}"},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "missing_fields"
    assert detail["category"] == "deadline"
    assert "deadline_date" in detail["fields"]
    assert "validation error" not in detail["message"].lower()
