"""FastAPI dependency providers for the responsibility graph (P6)."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_geometry_provider,
    get_temporal_engine,
)
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.graph.graph_service import ResponsibilityGraphService


def get_graph_service(
    db: Session = Depends(get_db),
    engine: TemporalJurisdictionEngine = Depends(get_temporal_engine),
    provider: ShapelyGeometryProvider = Depends(get_geometry_provider),
) -> ResponsibilityGraphService:
    """Deterministic responsibility-graph wiring (P6)."""
    return ResponsibilityGraphService(db=db, engine=engine, provider=provider)