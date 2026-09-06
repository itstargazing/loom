"""The skill endpoints are generated from a registry, so the wiring is tested.

Anything needing a live query is left to the curl checks in the README; what
matters here is that the registry stays in sync with the stores, that every
generated route carries a distinct response model, and that none of them are
reachable without a token.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import Base
from app.core.security import get_current_user_id
from app.main import app
from app.models.skill_stores import SkillEntry
from app.routers.skills import SKILL_RESOURCES, SKILLS_BY_SLUG
from app.services.skill_router import ROUTES


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        yield async_client


def test_registry_covers_every_skill_store():
    """A store with no endpoint would be invisible to the dashboard."""
    stores = {
        mapper.class_
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, SkillEntry)
    }
    exposed = {resource.model for resource in SKILL_RESOURCES}

    assert stores == exposed


def test_every_routed_category_has_a_reachable_store():
    """Routing somewhere the API cannot read would silently swallow data."""
    routed_models = {route.model for route in ROUTES.values()}
    exposed = {resource.model for resource in SKILL_RESOURCES}

    assert routed_models <= exposed


def test_slugs_are_unique():
    slugs = [resource.slug for resource in SKILL_RESOURCES]
    assert len(slugs) == len(set(slugs)) == len(SKILLS_BY_SLUG)


def test_generated_routes_keep_distinct_response_models():
    """A shared response model would drop skill-specific fields on serialize."""
    list_paths = {f"/api/skills/{resource.slug}" for resource in SKILL_RESOURCES}
    by_path = {
        route.path: route
        for route in app.routes
        if getattr(route, "path", "") in list_paths
    }

    assert len(by_path) == len(SKILL_RESOURCES)

    for resource in SKILL_RESOURCES:
        route = by_path[f"/api/skills/{resource.slug}"]
        assert route.response_model == list[resource.schema]


def test_openapi_schema_builds():
    """Generated routes are a common source of unserialisable OpenAPI schemas."""
    schema = app.openapi()

    for resource in SKILL_RESOURCES:
        assert f"/api/skills/{resource.slug}" in schema["paths"]
    assert "/api/collections" in schema["paths"]
    assert "/api/skills/glossary/{entry_id}" in schema["paths"]
    assert "patch" in schema["paths"]["/api/skills/glossary/{entry_id}"]
    assert "delete" in schema["paths"]["/api/skills/glossary/{entry_id}"]
    assert "/api/skills/citations/{entry_id}" in schema["paths"]
    assert "patch" in schema["paths"]["/api/skills/citations/{entry_id}"]
    assert "delete" in schema["paths"]["/api/skills/citations/{entry_id}"]
    assert "/api/skills/citations/export" in schema["paths"]
    assert "/api/skills/deadlines/{entry_id}" in schema["paths"]
    assert "patch" in schema["paths"]["/api/skills/deadlines/{entry_id}"]
    assert "/api/skills/contradictions" in schema["paths"]
    assert "/api/skills/contradictions/{entry_id}" in schema["paths"]
    assert "patch" in schema["paths"]["/api/skills/contradictions/{entry_id}"]
    assert "delete" in schema["paths"]["/api/skills/contradictions/{entry_id}"]
    assert "/api/skills/reading/compile" in schema["paths"]
    assert "/api/skills/reading/export" in schema["paths"]
    assert "/api/skills/reading/{entry_id}" in schema["paths"]
    assert "patch" in schema["paths"]["/api/skills/reading/{entry_id}"]
    assert "delete" in schema["paths"]["/api/skills/reading/{entry_id}"]
    assert "/api/skills/form-filler/profiles" in schema["paths"]
    assert "/api/skills/form-filler/documents" in schema["paths"]
    assert "/api/skills/form-filler/match" in schema["paths"]
    assert "/api/skills/form-filler/fill" in schema["paths"]
    assert "/api/skills/products/compare" in schema["paths"]
    assert "/api/skills/products/export" in schema["paths"]
    assert "/api/skills/products/{entry_id}" in schema["paths"]
    assert "/api/skills/jobs/{entry_id}" in schema["paths"]
    assert "delete" in schema["paths"]["/api/skills/jobs/{entry_id}"]
    assert "/api/skills/contract-flags/{entry_id}" in schema["paths"]
    assert "delete" in schema["paths"]["/api/skills/contract-flags/{entry_id}"]
    assert "/api/skills/live-doc-diff/sets" in schema["paths"]
    assert "/api/skills/live-doc-diff/unread" in schema["paths"]
    assert "/api/skills/live-doc-diff/sets/{set_id}/scan" in schema["paths"]
    assert "/api/skills/auto-attach/documents" in schema["paths"]
    assert "/api/skills/auto-attach/match" in schema["paths"]
    assert "/api/privacy/settings" in schema["paths"]
    assert "/api/privacy/local-mode" in schema["paths"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/overview",
        "/api/collections",
        "/api/skills/form-filler/profiles",
        "/api/skills/form-filler/documents",
        "/api/skills/products/compare",
        "/api/skills/products/export",
        "/api/skills/live-doc-diff/sets",
        "/api/skills/live-doc-diff/unread",
        "/api/skills/auto-attach/documents",
        "/api/privacy/settings",
        *[f"/api/skills/{resource.slug}" for resource in SKILL_RESOURCES],
    ],
)
async def test_skill_endpoints_require_a_token(client, path):
    response = await client.get(path)
    assert response.status_code == 403


async def test_collection_name_cannot_be_blank(client):
    """Validated before any database work, so no session is needed."""
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        response = await client.post("/api/collections", json={"name": "   "})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


async def test_glossary_patch_with_no_fields_is_rejected(client):
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        response = await client.patch(
            "/api/skills/glossary/00000000-0000-0000-0000-000000000001",
            json={},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


async def test_glossary_mutation_requires_a_token(client):
    entry = "/api/skills/glossary/00000000-0000-0000-0000-000000000001"
    assert (await client.patch(entry, json={"term": "x"})).status_code == 403
    assert (await client.delete(entry)).status_code == 403


async def test_citation_patch_with_no_fields_is_rejected(client):
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        response = await client.patch(
            "/api/skills/citations/00000000-0000-0000-0000-000000000001",
            json={},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


async def test_citation_mutation_and_export_require_a_token(client):
    entry = "/api/skills/citations/00000000-0000-0000-0000-000000000001"
    assert (await client.patch(entry, json={"author": "x"})).status_code == 403
    assert (await client.delete(entry)).status_code == 403
    assert (await client.get("/api/skills/citations/export")).status_code == 403


async def test_deadline_patch_with_no_fields_is_rejected(client):
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        response = await client.patch(
            "/api/skills/deadlines/00000000-0000-0000-0000-000000000001",
            json={},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


async def test_deadline_mutation_requires_a_token(client):
    entry = "/api/skills/deadlines/00000000-0000-0000-0000-000000000001"
    assert (await client.patch(entry, json={"confirmed": True})).status_code == 403
    assert (await client.delete(entry)).status_code == 403


async def test_product_patch_with_no_fields_is_rejected(client):
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        response = await client.patch(
            "/api/skills/products/00000000-0000-0000-0000-000000000001",
            json={},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


async def test_product_mutation_and_export_require_a_token(client):
    entry = "/api/skills/products/00000000-0000-0000-0000-000000000001"
    assert (await client.patch(entry, json={"price": "$1"})).status_code == 403
    assert (await client.delete(entry)).status_code == 403
    assert (await client.get("/api/skills/products/export")).status_code == 403


async def test_job_and_contract_delete_require_a_token(client):
    assert (
        await client.delete("/api/skills/jobs/00000000-0000-0000-0000-000000000001")
    ).status_code == 403
    assert (
        await client.delete(
            "/api/skills/contract-flags/00000000-0000-0000-0000-000000000001"
        )
    ).status_code == 403
