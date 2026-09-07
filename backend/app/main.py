import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai import close_ai_client
from app.core.config import settings
from app.core.database import engine
from app.core.redis import close_redis
from app.routers import (
    ask,
    auth,
    auto_attach,
    briefs,
    capture,
    classifications,
    digest,
    form_filler,
    health,
    live_doc_diff,
    notifications,
    overview,
    privacy,
    skills,
    trail,
)
from app.services.capture_queue import capture_stream
from app.services.classification_queue import classification_stream

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Created up front so the very first batch has somewhere to go even if no
    # worker has started yet.
    for stream in (capture_stream, classification_stream):
        try:
            await stream.ensure_group()
        except Exception:
            logger.exception("Could not initialize stream %s", stream.name)

    yield

    await close_ai_client()
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title="LOOM API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(capture.router)
app.include_router(classifications.router)
app.include_router(digest.router)
app.include_router(ask.router)
app.include_router(trail.router)
app.include_router(briefs.router)
app.include_router(notifications.router)
app.include_router(skills.router)
app.include_router(form_filler.router)
app.include_router(live_doc_diff.router)
app.include_router(auto_attach.router)
app.include_router(privacy.router)
app.include_router(overview.router)


@app.get("/")
async def root():
    return {"name": "LOOM API", "version": "0.1.0"}
