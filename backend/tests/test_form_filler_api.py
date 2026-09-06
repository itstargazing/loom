"""Form-filler endpoints reject unauthenticated and empty payloads without a database."""

from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user_id
from app.main import app


async def test_form_filler_routes_require_a_token():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/api/skills/form-filler/profiles")).status_code == 403
        assert (await client.get("/api/skills/form-filler/documents")).status_code == 403
        assert (
            await client.post(
                "/api/skills/form-filler/match",
                json={
                    "profileId": "00000000-0000-0000-0000-000000000001",
                    "documentIds": [],
                },
            )
        ).status_code == 403
        assert (
            await client.post(
                "/api/skills/form-filler/fill",
                json={
                    "profileId": "00000000-0000-0000-0000-000000000001",
                    "documentIds": ["00000000-0000-0000-0000-000000000002"],
                },
            )
        ).status_code == 403


async def test_blank_profile_name_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/skills/form-filler/profiles", json={"name": "   "}
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


async def test_profile_patch_with_no_fields_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/skills/form-filler/profiles/00000000-0000-0000-0000-000000000001",
                json={},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


async def test_match_without_documents_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/skills/form-filler/match",
                json={
                    "profileId": "00000000-0000-0000-0000-000000000001",
                    "documentIds": [],
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


async def test_non_pdf_upload_is_rejected():
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/skills/form-filler/documents",
                files={"file": ("notes.txt", b"not a pdf", "text/plain")},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
