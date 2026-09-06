"""Auto-attach endpoints reject unauthenticated and empty payloads without a database."""

from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user_id
from app.main import app


async def test_auto_attach_routes_require_a_token():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/skills/auto-attach/documents")).status_code == 403
        assert (
            await client.post(
                "/api/skills/auto-attach/match",
                json={"labelText": "Resume"},
            )
        ).status_code == 403


async def test_blank_filename_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/skills/auto-attach/documents",
                json={"filename": "  "},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
