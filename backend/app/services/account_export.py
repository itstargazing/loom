"""Account data export (GDPR-style portability)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import UserAccount
from app.models.capture_event import CaptureEvent
from app.models.event_classification import EventClassification
from app.models.privacy import UserPrivacySettings
from app.models.skill_stores import (
    Citation,
    ContractFlag,
    Contradiction,
    Deadline,
    GlossaryTerm,
    JobListing,
    ProductListing,
    ReadingCompilerEntry,
)
from app.services.quotas import quota_status


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


async def _rows(session: AsyncSession, model, user_id: str, limit: int = 10_000) -> list[dict]:
    result = await session.execute(
        select(model).where(model.user_id == user_id).limit(limit)
    )
    out: list[dict] = []
    for row in result.scalars().all():
        data = {col.name: _jsonable(getattr(row, col.name)) for col in model.__table__.columns}
        out.append(data)
    return out


async def build_account_export(session: AsyncSession, user_id: str) -> dict[str, Any]:
    account = (
        await session.execute(select(UserAccount).where(UserAccount.user_id == user_id))
    ).scalar_one_or_none()
    privacy = (
        await session.execute(
            select(UserPrivacySettings).where(UserPrivacySettings.user_id == user_id)
        )
    ).scalar_one_or_none()

    payload = {
        "exportedAt": datetime.utcnow().isoformat() + "Z",
        "userId": user_id,
        "account": (
            {col.name: _jsonable(getattr(account, col.name)) for col in UserAccount.__table__.columns}
            if account
            else None
        ),
        "privacy": (
            {
                col.name: _jsonable(getattr(privacy, col.name))
                for col in UserPrivacySettings.__table__.columns
            }
            if privacy
            else None
        ),
        "quotas": await quota_status(user_id, session),
        "captureEvents": await _rows(session, CaptureEvent, user_id),
        "classifications": await _rows(session, EventClassification, user_id),
        "citations": await _rows(session, Citation, user_id),
        "deadlines": await _rows(session, Deadline, user_id),
        "glossaryTerms": await _rows(session, GlossaryTerm, user_id),
        "readingEntries": await _rows(session, ReadingCompilerEntry, user_id),
        "productListings": await _rows(session, ProductListing, user_id),
        "jobListings": await _rows(session, JobListing, user_id),
        "contractFlags": await _rows(session, ContractFlag, user_id),
        "contradictions": await _rows(session, Contradiction, user_id),
    }
    return payload


def export_as_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2, default=str).encode("utf-8")
