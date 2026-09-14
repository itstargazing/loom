from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.database import engine
from app.core.redis import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Liveness — process is up. Does not check dependencies."""
    return {"status": "ok"}


@router.get("/ready")
async def ready_check(response: Response):
    """Readiness — Postgres and Redis must answer."""
    checks: dict[str, str] = {}
    ok = True

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as error:
        ok = False
        checks["postgres"] = f"error: {error.__class__.__name__}"

    try:
        pong = await redis_client.ping()
        checks["redis"] = "ok" if pong else "error: no pong"
        if not pong:
            ok = False
    except Exception as error:
        ok = False
        checks["redis"] = f"error: {error.__class__.__name__}"

    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "checks": checks}

    return {"status": "ready", "checks": checks}
