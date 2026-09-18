"""FastAPI dependency providers for the responsibility conflict detector (P5)."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_geometry_provider,
    get_temporal_engine,
)
from app.conflicts.conflict_service import ResponsibilityConflictService
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine


def get_conflict_service(
    db: Session = Depends(get_db),
    engine: TemporalJurisdictionEngine = Depends(get_temporal_engine),
    provider: ShapelyGeometryProvider = Depends(get_geometry_provider),
) -> ResponsibilityConflictService:
    """Deterministic responsibility conflict detector wiring (P5)."""
    return ResponsibilityConflictService(db=db, engine=engine, provider=provider)