"""Responsibility graph API (P6).

Deterministic explanatory view of an existing P2 routing decision: the graph
consumes ``ResponsibilityRoutingService.resolve`` and projects the result onto
the chain Location → Jurisdiction → Authority → Department → Service → Issue →
Escalation. It never re-implements routing decisions and never stores
anything — only the P2 routing audit row is persisted, exactly as the P2
``/routing/resolve`` endpoint already does.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_graph import get_graph_service
from app.graph.graph_service import ResponsibilityGraphService
from app.schemas.graph import GraphResolveResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get(
    "/resolve",
    response_model=GraphResolveResponse,
    summary="Explanatory responsibility chain for a location+issue+date",
)
def resolve_graph(
    lat: float = Query(description="Latitude in WGS84 degrees"),
    lng: float = Query(description="Longitude in WGS84 degrees"),
    issue_type: str = Query(description="Issue code from the issue-type registry"),
    date: date = Query(description="Temporal point of the routing decision"),
    service: ResponsibilityGraphService = Depends(get_graph_service),
    db: Session = Depends(get_db),
) -> GraphResolveResponse:
    response = service.resolve(
        latitude=lat,
        longitude=lng,
        issue_type=issue_type,
        on_date=date,
    )
    db.commit()
    return response