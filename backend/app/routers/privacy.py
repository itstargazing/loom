"""Local-only sensitive mode: domain policy and status checks."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.privacy import UserPrivacySettings
from app.schemas.privacy import LocalModeCheckOut, PrivacySettingsIn, PrivacySettingsOut
from app.services.local_mode import (
    hostname_of,
    matches_local_domain,
    normalize_domain_pattern,
)

router = APIRouter(prefix="/api", tags=["privacy"])


def _default_domains() -> list[str]:
    return [
        normalize_domain_pattern(item)
        for item in settings.local_only_domains_default
        if normalize_domain_pattern(item)
    ]


def _effective_domains(row: UserPrivacySettings | None) -> list[str]:
    user = list(row.local_only_domains) if row else []
    merged: list[str] = []
    seen: set[str] = set()
    for pattern in [*user, *_default_domains()]:
        if pattern in seen:
            continue
        seen.add(pattern)
        merged.append(pattern)
    return merged


def _settings_out(row: UserPrivacySettings | None) -> PrivacySettingsOut:
    return PrivacySettingsOut(
        local_only_domains=list(row.local_only_domains) if row else [],
        default_domains=_default_domains(),
        effective_domains=_effective_domains(row),
        updated_at=row.updated_at if row else None,
    )


async def _load_row(
    db: AsyncSession, user_id: str
) -> UserPrivacySettings | None:
    result = await db.execute(
        select(UserPrivacySettings).where(UserPrivacySettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


@router.get(
    "/privacy/settings",
    response_model=PrivacySettingsOut,
    summary="Local-only domain list and tradeoff note",
)
async def get_privacy_settings(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PrivacySettingsOut:
    return _settings_out(await _load_row(db, user_id))


@router.put(
    "/privacy/settings",
    response_model=PrivacySettingsOut,
    summary="Replace the user's local-only domain list",
)
async def put_privacy_settings(
    payload: PrivacySettingsIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PrivacySettingsOut:
    row = await _load_row(db, user_id)
    if row is None:
        row = UserPrivacySettings(
            user_id=user_id, local_only_domains=payload.local_only_domains
        )
        db.add(row)
    else:
        row.local_only_domains = payload.local_only_domains
    await db.commit()
    await db.refresh(row)
    return _settings_out(row)


@router.get(
    "/privacy/local-mode",
    response_model=LocalModeCheckOut,
    summary="Check whether a URL would use local classification",
)
async def check_local_mode(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
    url: Annotated[str, Query(min_length=1)],
) -> LocalModeCheckOut:
    row = await _load_row(db, user_id)
    domains = _effective_domains(row)
    host = hostname_of(url)
    matched: str | None = None
    for pattern in domains:
        if matches_local_domain(url, [pattern]):
            matched = pattern
            break
    return LocalModeCheckOut(
        url=url,
        hostname=host,
        local_mode=matched is not None,
        matched_pattern=matched,
    )
