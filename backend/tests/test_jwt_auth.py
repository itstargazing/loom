"""JWT auth mode and production startup guard."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import assert_auth_safe_for_environment, get_current_user_id
from app.main import app


def _mint(sub: str, *, secret: str | None = None, hours: int = 1) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": sub, "iat": now, "exp": now + timedelta(hours=hours)},
        secret or settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture
def jwt_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_mode", "jwt")
    monkeypatch.setattr(settings, "jwt_secret", "test-jwt-secret")
    monkeypatch.setattr(settings, "jwt_algorithms", "HS256")
    monkeypatch.setattr(settings, "jwt_jwks_url", "")
    monkeypatch.setattr(settings, "jwt_audience", "")
    monkeypatch.setattr(settings, "jwt_issuer", "")
    yield
    app.dependency_overrides.clear()


async def test_jwt_mode_maps_sub_to_user_id(jwt_mode):
    token = _mint("alice")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/auth/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["userId"] == "alice"
    assert body["authMode"] == "jwt"
    assert body["providerReady"] is True


async def test_jwt_mode_rejects_bad_signature(jwt_mode):
    token = _mint("alice", secret="wrong-secret")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/auth/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 401


async def test_different_jwt_subjects_are_different_users(jwt_mode):
    alice = await get_current_user_id(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=_mint("alice"))
    )
    bob = await get_current_user_id(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=_mint("bob"))
    )
    assert alice == "alice"
    assert bob == "bob"
    assert alice != bob


def test_production_refuses_stub_auth(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "auth_mode", "stub")
    with pytest.raises(RuntimeError, match="AUTH_MODE=stub"):
        assert_auth_safe_for_environment()


def test_production_allows_jwt(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "auth_mode", "jwt")
    assert_auth_safe_for_environment()
