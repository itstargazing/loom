"""Stripe Checkout / Customer Portal / webhooks for Pro plan."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import CurrentUserId
from app.models.account import UserAccount
from app.services.quotas import quota_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _stripe():
    if not settings.stripe_secret_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured (STRIPE_SECRET_KEY).",
        )
    try:
        import stripe
    except ImportError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="stripe package is not installed.",
        ) from error
    stripe.api_key = settings.stripe_secret_key.strip()
    return stripe


async def _ensure_account(db: AsyncSession, user_id: str) -> UserAccount:
    result = await db.execute(select(UserAccount).where(UserAccount.user_id == user_id))
    account = result.scalar_one_or_none()
    if account is not None:
        return account
    account = UserAccount(
        user_id=user_id,
        display_name=user_id,
        auth_mode=(settings.auth_mode or "stub").strip().lower(),
        plan="free",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/status")
async def billing_status(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    account = await _ensure_account(db, user_id)
    quotas = await quota_status(user_id, db)
    return {
        "plan": account.plan,
        "stripeConfigured": bool(settings.stripe_secret_key.strip()),
        "stripeCustomerId": account.stripe_customer_id,
        "stripeSubscriptionId": account.stripe_subscription_id,
        "quotas": quotas,
        "captureRetentionDays": settings.capture_retention_days,
        "skillRetentionDays": settings.skill_retention_days,
        "orgDataNote": (
            "Team seats use Clerk Organizations for membership and billing. "
            "Capture and skill data remain personal to each user_id until "
            "org-scoped stores ship."
        ),
    }


@router.post("/checkout")
async def create_checkout(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    stripe = _stripe()
    if not settings.stripe_price_pro.strip():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="STRIPE_PRICE_PRO unset")
    success = settings.billing_success_url.strip() or "http://localhost:3000/account?billing=success"
    cancel = settings.billing_cancel_url.strip() or "http://localhost:3000/account?billing=cancel"

    account = await _ensure_account(db, user_id)
    customer_id = account.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            metadata={"loom_user_id": user_id},
            email=account.email or None,
        )
        customer_id = customer["id"]
        account.stripe_customer_id = customer_id
        await db.commit()

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": settings.stripe_price_pro.strip(), "quantity": 1}],
        success_url=success,
        cancel_url=cancel,
        client_reference_id=user_id,
        metadata={"loom_user_id": user_id},
    )
    return {"url": session["url"], "sessionId": session["id"]}


@router.post("/portal")
async def create_portal(
    user_id: CurrentUserId,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    stripe = _stripe()
    account = await _ensure_account(db, user_id)
    if not account.stripe_customer_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No Stripe customer yet. Start checkout first.")
    return_url = settings.billing_success_url.strip() or "http://localhost:3000/account"
    session = stripe.billing_portal.Session.create(
        customer=account.stripe_customer_id,
        return_url=return_url,
    )
    return {"url": session["url"]}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
) -> dict:
    stripe = _stripe()
    payload = await request.body()
    secret = settings.stripe_webhook_secret.strip()
    if not secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="STRIPE_WEBHOOK_SECRET unset")
    if not stripe_signature:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, secret)
    except Exception as error:
        logger.warning("Stripe webhook rejected: %s", error)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid webhook") from error

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = (data.get("client_reference_id") or data.get("metadata", {}).get("loom_user_id"))
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id:
            account = await _ensure_account(db, user_id)
            account.plan = "pro"
            if customer_id:
                account.stripe_customer_id = customer_id
            if subscription_id:
                account.stripe_subscription_id = subscription_id
            await db.commit()

    elif event_type in {"customer.subscription.deleted", "customer.subscription.updated"}:
        customer_id = data.get("customer")
        status_value = data.get("status")
        result = await db.execute(
            select(UserAccount).where(UserAccount.stripe_customer_id == customer_id)
        )
        account = result.scalar_one_or_none()
        if account is not None:
            if event_type == "customer.subscription.deleted" or status_value in {
                "canceled",
                "unpaid",
                "incomplete_expired",
            }:
                account.plan = "free"
                account.stripe_subscription_id = None
            elif status_value in {"active", "trialing"}:
                account.plan = "pro"
                account.stripe_subscription_id = data.get("id")
            await db.commit()

    return {"received": True}
