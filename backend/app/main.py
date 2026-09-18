"""FastAPI application entrypoint.

Startup lifecycle: create tables (SQLite) and load deterministic demo data.
All endpoints are versioned under ``/api/v1``.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.gis import router as gis_router
from app.api.routers.health import router as health_router
from app.api.routers.routing import router as routing_router
from app.api.routers.whatif import router as whatif_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.db.session import SessionLocal, init_db
from app.logging_config import configure_logging
from app.schemas.common import ApiInfo
from app.seed.seed_runner import seed_all

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialise the database and load deterministic demo data on startup."""
    init_db()
    if settings.seed_on_startup:
        with SessionLocal() as session:
            stats = seed_all(session)
            session.commit()
            logger.info("Seed load summary: %s", stats.summary)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Determines the responsible civic authority, department and "
    "service for a location + issue while honoring jurisdiction boundaries "
    "that change over time.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.get("/", response_model=ApiInfo, tags=["meta"])
def root() -> ApiInfo:
    """Service metadata; replaces a plain 404 at the API root."""
    return ApiInfo(name=settings.app_name, version=settings.app_version, docs="/docs")


app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(gis_router, prefix=settings.api_v1_prefix)
app.include_router(routing_router, prefix=settings.api_v1_prefix)
app.include_router(whatif_router, prefix=settings.api_v1_prefix)