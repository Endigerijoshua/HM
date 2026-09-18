"""Historical jurisdiction replay API (P7).

Deterministic, read-only chronological replay for one (location, issue) across
a date range. Every sampled day is resolved independently through the P2
routing service; consecutive identical outcomes are merged into periods so
boundary transitions (jurisdiction version changes, routing-rule effective
dates, responsibility gaps) are explicit. Replay never commits, so no audit row
is persisted for the replayed days.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_routing_service
from app.replay.replay_service import replay_point
from app.routing.routing_service import ResponsibilityRoutingService
from app.schemas.replay import ReplayPointResponse

router = APIRouter(prefix="/replay", tags=["replay"])


@router.get(
    "/point",
    response_model=ReplayPointResponse,
    summary="Replay historical responsibility for a point across a date range",
)
def replay_point_endpoint(
    latitude: float = Query(description="Latitude in WGS84 degrees"),
    longitude: float = Query(description="Longitude in WGS84 degrees"),
    issue_type: str = Query(description="Issue code from the issue-type registry"),
    start_date: date = Query(description="Inclusive start of the replay window"),
    end_date: date = Query(description="Exclusive end of the replay window"),
    routing_service: ResponsibilityRoutingService = Depends(get_routing_service),
) -> ReplayPointResponse:
    return replay_point(
        routing_service=routing_service,
        latitude=latitude,
        longitude=longitude,
        issue_type=issue_type,
        start=start_date,
        end=end_date,
    )