"""Auth endpoints reject unauthenticated requests without a database."""

from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
import pytest

from app.core.security import get_current_user_id
from app.main import app
from app.schemas.auth import AccountPatch, DeleteAccountIn
from app.services.rate_limit import SlidingWindowLimiter
from app.services.sanitize import sanitize_plain_text


async def test_auth_routes_require_a_token():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/auth/me")).status_code == 403
        assert (await client.get("/api/auth/status")).status_code == 403
        assert (await client.post("/api/auth/logout")).status_code == 403
        assert (
            await client.request(
                "DELETE", "/api/auth/me", json={"confirm": "DELETE"}
            )
        ).status_code == 403


async def test_auth_status_describes_stub_mode(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "auth_mode", "stub")
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["userId"] == "dev-user"
    assert body["authMode"] == "stub"
    assert body["providerReady"] is False
    assert "environment" in body
    assert "multi-user" in body["detail"].casefold()


async def test_logout_is_a_client_side_hint():
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/auth/logout")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "session" in body["detail"].casefold()


async def test_account_patch_with_no_fields_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch("/api/auth/me", json={})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


async def test_delete_account_requires_exact_confirmation():
    with pytest.raises(ValidationError, match="DELETE"):
        DeleteAccountIn(confirm="delete")
    DeleteAccountIn(confirm="DELETE")


def test_account_patch_requires_a_field():
    with pytest.raises(ValidationError, match="No fields to update"):
        AccountPatch()


def test_classification_rate_limiter_trips_after_the_window_fills():
    limiter = SlidingWindowLimiter()
    limiter.check("user-a", limit=2, window_seconds=60)
    limiter.check("user-a", limit=2, window_seconds=60)
    with pytest.raises(Exception) as caught:
        limiter.check("user-a", limit=2, window_seconds=60)
    assert caught.value.status_code == 429
    #  A different user is not blocked by the first bucket.
    limiter.check("user-b", limit=2, window_seconds=60)


def test_sanitize_strips_tags_and_collapses_space():
    assert sanitize_plain_text("  <b>Dev</b>   user  ") == "Dev user"
    assert sanitize_plain_text("") == ""
    assert len(sanitize_plain_text("x" * 400, max_len=10)) == 10
