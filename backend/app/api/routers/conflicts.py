"""Responsibility conflict detector API (P5).

Deterministic and explainable. ``GET`` endpoints only read persisted
conflicts; ``POST /conflicts/detect`` re-runs the detector against the live
jurisdictions and routing table, persisting any *new* conflict. Rerunning the
detector is safe — identical open conflicts are never duplicated (a stable
compound key makes repeated results deterministic).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps_conflicts import get_conflict_service
from app.conflicts.conflict_service import ResponsibilityConflictService
from app.schemas.conflicts import (
    ConflictDetectResponse,
    ConflictListResponse,
    ConflictResponse,
)

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get(
    "",
    response_model=ConflictListResponse,
    summary="List detected responsibility conflicts",
)
def list_conflicts(
    status: str | None = Query(
        default=None,
        description="Optional status filter (OPEN, UNDER_REVIEW, RESOLVED, DISMISSED)",
    ),
    service: ResponsibilityConflictService = Depends(get_conflict_service),
) -> ConflictListResponse:
    return service.list_conflicts(status=status)


@router.get(
    "/{conflict_id}",
    response_model=ConflictResponse,
    summary="Get a single responsibility conflict",
)
def get_conflict(
    conflict_id: str,
    service: ResponsibilityConflictService = Depends(get_conflict_service),
) -> ConflictResponse:
    return service.get_conflict(conflict_id)


@router.post(
    "/detect",
    response_model=ConflictDetectResponse,
    summary="Run deterministic conflict detection against live data",
)
def detect(
    service: ResponsibilityConflictService = Depends(get_conflict_service),
) -> ConflictDetectResponse:
    return service.detect()