"""Health and diagnostics endpoints."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import get_settings
from app.db.models.reference import Authority
from app.db.session import db_healthcheck
from app.schemas.common import ApiHealth

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiHealth, summary="Service and database health")
def get_health(db: Session = Depends(get_db)) -> ApiHealth:
    settings = get_settings()
    seed_loaded = db.query(Authority.id).limit(1).first() is not None
    return ApiHealth(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
        database_status="ok" if db_healthcheck(db) else "error",
        seed_loaded=seed_loaded,
        geometry_engine=settings.geometry_engine,
        timestamp=datetime.now(timezone.utc),
    )