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
        auth_mode=(settings.auth_mode or "stub").strip().lower(),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


def _session_note(mode: str) -> str:
    if mode == "jwt":
        return (
            "Authenticated with a JWT. Your user id is the token subject (sub). "
            "Rotate or expire tokens in your identity provider (Clerk/Supabase)."
        )
    return (
        "Authenticated with the shared development bearer token. "
        "Every client shares one user — set AUTH_MODE=jwt before multi-user release."
    )


def _out(account: UserAccount) -> AccountOut:
    mode = (settings.auth_mode or "stub").strip().lower()
    return AccountOut(
        user_id=account.user_id,
        display_name=account.display_name,
        email=account.email,
        auth_mode=mode,
        created_at=account.created_at,
        updated_at=account.updated_at,
        session_note=_session_note(mode),
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
    mode = (settings.auth_mode or "stub").strip().lower()
    if mode == "jwt":
        return LogoutOut(
            detail=(
                "JWT auth has no server-side session store. "
                "Clear the bearer token on the client (and revoke it in Clerk/Supabase if needed)."
            )
        )
    return LogoutOut(
        detail=(
            "Stub auth has no server-side session. "
            "Clear LOOM_API_TOKEN / the extension sync token on the client."
        )
    )


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


@router.get("/status", summary="Auth mode and readiness (no secrets)")
async def auth_status(user_id: CurrentUserId) -> dict[str, str | bool]:
    mode = (settings.auth_mode or "stub").strip().lower()
    jwt_ready = mode == "jwt" and bool(
        settings.jwt_jwks_url.strip() or settings.jwt_secret.strip()
    )
    if mode == "jwt":
        detail = (
            "JWT auth is active. Each token subject maps to its own LOOM user id."
        )
    else:
        detail = (
            "Stub bearer auth is active — every client shares one user. "
            "Set AUTH_MODE=jwt before multi-user release."
        )
    return {
        "authenticated": True,
        "userId": user_id,
        "authMode": mode,
        "environment": settings.environment,
        "tokenConfigured": bool(settings.stub_auth_token) if mode == "stub" else jwt_ready,
        "providerReady": jwt_ready,
        "detail": detail,
    }
