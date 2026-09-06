"""Account profile and stub auth session endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.account import UserAccount
from app.schemas.auth import AccountOut, AccountPatch, DeleteAccountIn, LogoutOut
from app.services.account_purge import purge_user_data
from app.services.sanitize import sanitize_plain_text

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _ensure_account(db: AsyncSession, user_id: str) -> UserAccount:
    result = await db.execute(
        select(UserAccount).where(UserAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is not None:
        return account
    account = UserAccount(
        user_id=user_id,
        display_name=user_id,
        auth_mode="stub",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


def _out(account: UserAccount) -> AccountOut:
    return AccountOut(
        user_id=account.user_id,
        display_name=account.display_name,
        email=account.email,
        auth_mode=account.auth_mode,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("/me", response_model=AccountOut, summary="Current account profile")
async def get_me(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountOut:
    return _out(await _ensure_account(db, user_id))


@router.patch("/me", response_model=AccountOut, summary="Update account profile")
async def patch_me(
    payload: AccountPatch,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountOut:
    account = await _ensure_account(db, user_id)
    if "display_name" in payload.model_fields_set:
        name = sanitize_plain_text(payload.display_name or "")
        account.display_name = name or user_id
    if "email" in payload.model_fields_set:
        email = sanitize_plain_text(payload.email or "", max_len=320)
        account.email = email or None
    await db.commit()
    await db.refresh(account)
    return _out(account)


@router.post("/logout", response_model=LogoutOut, summary="Client logout helper")
async def logout(_user_id: CurrentUserId) -> LogoutOut:
    return LogoutOut()


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete account and all associated LOOM data",
)
async def delete_me(
    payload: DeleteAccountIn,
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    _ = payload  # validated by schema
    await purge_user_data(db, user_id)


@router.get("/status", summary="Auth mode and stub token hints (no secrets)")
async def auth_status(user_id: CurrentUserId) -> dict[str, str | bool]:
    return {
        "authenticated": True,
        "userId": user_id,
        "authMode": "stub",
        "tokenConfigured": bool(settings.stub_auth_token),
        "providerReady": False,
        "detail": "Stub bearer auth is active. Wire Clerk/Supabase to replace it.",
    }
