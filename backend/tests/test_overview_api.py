"""The overview endpoint builds its SQL dynamically from the skill registry.

There is no live database here, so these checks compile the statements against
the Postgres dialect and inspect the result. That catches the failure modes this
endpoint is most exposed to: a UNION ALL branch that disagrees with its
siblings, a registry entry pointing at a column that does not exist, and a
missing per-user filter.
"""

from typing import Any

from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.core.security import get_current_user_id
from app.main import app
from app.routers import overview
from app.routers.skills import SKILL_RESOURCES
from app.schemas.overview import ActivityItem


def compile_pg(statement: Any) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_every_skill_exposes_feed_columns():
    for resource in SKILL_RESOURCES:
        assert resource.title is not None, resource.slug
        assert resource.detail is not None, resource.slug


def test_activity_branches_agree_on_the_feed_shape():
    parts = overview.build_activity_parts("user-1")
    assert len(parts) == len(SKILL_RESOURCES)

    shapes = {tuple(part.selected_columns.keys()) for part in parts}
    assert len(shapes) == 1, f"branches disagree on columns: {shapes}"
    assert shapes.pop() == tuple(ActivityItem.model_fields)


def test_activity_feed_orders_and_limits_in_the_database():
    sql = compile_pg(overview.build_activity_query("user-1", 20))

    assert sql.count("UNION ALL") == len(SKILL_RESOURCES) - 1
    assert "last_seen_at DESC" in sql
    assert "LIMIT 20" in sql
    #  Every branch must be scoped to the caller, or one user sees another's
    #  captures in the feed.
    assert sql.count("user_id = 'user-1'") == len(SKILL_RESOURCES)
    #  Title and detail are trimmed by Postgres so the payload stays small.
    assert sql.count("left(CAST") == 2 * len(SKILL_RESOURCES)
    assert str(overview.FEED_TEXT_LIMIT) in sql


def test_skill_counts_use_one_subquery_per_store():
    sql = compile_pg(overview.build_counts_query("user-1"))

    assert sql.count("SELECT count(*)") == len(SKILL_RESOURCES)
    for resource in SKILL_RESOURCES:
        assert resource.slug.replace("-", "_") in sql


def test_pipeline_summaries_aggregate_in_one_pass():
    for statement in (
        overview.build_capture_query("user-1"),
        overview.build_classification_query("user-1"),
    ):
        sql = compile_pg(statement)
        assert "FILTER (WHERE" in sql
        assert "user_id = 'user-1'" in sql


async def test_activity_limit_is_bounded():
    """Rejected before any query runs, so no database is needed."""
    app.dependency_overrides[get_current_user_id] = lambda: "dev-user"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/overview", params={"activity_limit": 500})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_overview_response_is_camel_cased():
    """The dashboard consumes these keys directly."""
    schemas = app.openapi()["components"]["schemas"]

    assert set(schemas["DashboardOverview"]["properties"]) == {
        "skills",
        "recentActivity",
        "capture",
        "classification",
    }
    assert "lastEventAt" in schemas["CaptureSummary"]["properties"]
    assert "awaitingRouting" in schemas["ClassificationSummary"]["properties"]
