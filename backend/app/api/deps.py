"""FastAPI dependency providers."""
from __future__ import annotations

from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import ForbiddenError
from app.db.session import SessionLocal
from app.gis.base import GeometryNotAvailableError
from app.gis.ops import GisService
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.routing.routing_service import ResponsibilityRoutingService


def get_db() -> Iterator[Session]:
    """Yield a SQLAlchemy session for the request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_geometry_provider(db: Session = Depends(get_db)) -> ShapelyGeometryProvider:
    """Wire the configured geometry engine. P0 supports only the Shapely store."""
    settings = get_settings()
    if settings.geometry_engine not in {"shapely", "sqlite", "demo"}:
        raise GeometryNotAvailableError(
            f"Geometry engine {settings.geometry_engine!r} is not available in this build"
        )
    return ShapelyGeometryProvider(db)


def get_gis_service(provider: ShapelyGeometryProvider = Depends(get_geometry_provider)) -> GisService:
    """Wire the GIS service layer on top of the configured geometry engine."""
    return GisService(provider)


def get_temporal_engine(
    provider: ShapelyGeometryProvider = Depends(get_geometry_provider),
) -> TemporalJurisdictionEngine:
    """Wire the temporal jurisdiction resolution engine."""
    return TemporalJurisdictionEngine(provider)


def get_routing_service(
    db: Session = Depends(get_db),
    provider: ShapelyGeometryProvider = Depends(get_geometry_provider),
    engine: TemporalJurisdictionEngine = Depends(get_temporal_engine),
) -> ResponsibilityRoutingService:
    """Wire the civic responsibility routing service (P2)."""
    return ResponsibilityRoutingService(db, engine, provider)


def require_admin(request: Request) -> None:
    """Demo-grade guard for admin endpoints (used from P1 onward)."""
    settings = get_settings()
    if not settings.admin_token:
        raise ForbiddenError("Admin endpoints are disabled until an admin token is configured")
    expected = settings.admin_token
    provided = request.headers.get("X-Admin-Token")
    if provided != expected:
        raise ForbiddenError("Valid admin credentials are required")