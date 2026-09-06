"""Privacy endpoints reject unauthenticated requests without a database."""

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_privacy_routes_require_a_token():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/privacy/settings")).status_code == 403
        assert (
            await client.get(
                "/api/privacy/local-mode",
                params={"url": "https://bank.example.com/"},
            )
        ).status_code == 403
        assert (
            await client.put(
                "/api/privacy/settings",
                json={"localOnlyDomains": ["intranet.example.com"]},
            )
        ).status_code == 403
