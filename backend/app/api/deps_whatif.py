"""FastAPI dependency providers for the what-if simulator (P3)."""
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
from app.whatif.whatif_service import WhatIfSimulationService


def get_whatif_service(
    db: Session = Depends(get_db),
    engine: TemporalJurisdictionEngine = Depends(get_temporal_engine),
    provider: ShapelyGeometryProvider = Depends(get_geometry_provider),
) -> WhatIfSimulationService:
    """Deterministic, read-only what-if simulator wiring (P3)."""
    return WhatIfSimulationService(db=db, engine=engine, provider=provider)
