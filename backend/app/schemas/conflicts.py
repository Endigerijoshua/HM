"""Pydantic schemas for the responsibility conflict detector API (P5).

A conflict is a deterministic, explainable disagreement between the
jurisdiction geography (expected responsibility) and the routing decision
table (routed responsibility), or a gap where no responsibility can be
established. ``conflict_type`` is an open string so legacy rows
(e.g. ``GEO_VS_SERVICE``) remain serializable; the detector emits
``AUTHORITY_MISMATCH`` | ``DEPARTMENT_MISMATCH`` | ``SERVICE_MISMATCH`` |
``TEMPORAL_RULE_CONFLICT`` | ``RESPONSIBILITY_GAP``.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.routing import ActorRef


class ConflictResponse(BaseModel):
    """A single detected responsibility conflict."""

    model_config = ConfigDict(populate_by_name=True)

    conflict_id: str
    latitude: float
    longitude: float
    complaint_ref: str | None = None
    issue_type: str | None = None
    issue_type_name: str | None = None
    # Wire key is "date" (the temporal point the conflict was evaluated on); the
    # Python attribute is "on_date" so it cannot clash with the `date` type.
    on_date: date | None = Field(default=None, alias="date")
    jurisdiction_code: str | None = None
    jurisdiction_name: str | None = None
    expected_authority: ActorRef | None = None
    routed_authority: ActorRef | None = None
    expected_department: ActorRef | None = None
    routed_department: ActorRef | None = None
    expected_service: ActorRef | None = None
    routed_service: ActorRef | None = None
    conflict_type: str
    severity: str | None = None
    explanation: str
    status: str
    created_at: str | None = None


class ConflictListResponse(BaseModel):
    """Collection envelope for GET /conflicts."""

    count: int
    conflicts: list[ConflictResponse]


class ConflictDetectResponse(BaseModel):
    """Result of a detection run (POST /conflicts/detect).

    ``conflicts`` holds only the rows *created by this run*; a repeat run with
    no new conflicts therefore returns an empty list and ``created == 0``.
    """

    detection_date: date
    evaluated: int
    created: int
    count: int
    conflicts: list[ConflictResponse] = Field(
        default_factory=list, description="The newly created conflicts"
    )