"""Pydantic schemas for the civic responsibility routing API (P2).

Routing decisions intentionally return HTTP 200 with a ``status`` field: every
outcome — a successful route, an unresolved responsibility conflict, a temporal
data conflict, an out-of-window date or an unknown issue — is a *valid answer*
the citizen is shown, not a server error. Only malformed requests (e.g. out of
WGS84 coordinate bounds) fail validation with a 422.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RoutingStatus(str, Enum):
    """Outcome of a routing resolution."""

    RESOLVED = "RESOLVED"
    RESPONSIBILITY_UNRESOLVED = "RESPONSIBILITY_UNRESOLVED"
    NO_JURISDICTION = "NO_JURISDICTION"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"
    INVALID_LOCATION = "INVALID_LOCATION"
    INVALID_ISSUE = "INVALID_ISSUE"
    INVALID_DATE = "INVALID_DATE"


class RouteResolveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    latitude: float = Field(ge=-90.0, le=90.0, description="Latitude in WGS84 degrees")
    longitude: float = Field(ge=-180.0, le=180.0, description="Longitude in WGS84 degrees")
    issue_type: str = Field(min_length=1, description="Issue code from the issue-type registry")
    # Wire key is "date" (matches the GIS lookup convention); the Python attribute
    # is "on_date" so it cannot clash with the `date` type annotation.
    on_date: date = Field(default_factory=date.today, alias="date", description="Temporal point of the routing query")


class ActorRef(BaseModel):
    id: int
    code: str
    name: str


class EscalationStepRef(BaseModel):
    step_number: int
    authority: ActorRef
    department: ActorRef
    service: ActorRef
    note: str | None = None


class RoutingResult(BaseModel):
    status: RoutingStatus
    latitude: float
    longitude: float
    issue_type: str
    effective_date: date

    # Geographic context (populated whenever the engine found a jurisdiction).
    jurisdiction_code: str | None = None
    jurisdiction_name: str | None = None
    jurisdiction_kind: str | None = None
    version_code: str | None = None
    version_status: str | None = None
    ward_code: str | None = None
    ward_name: str | None = None

    # Responsible actor (populated for RESOLVED).
    matched_scope: str | None = None
    authority: ActorRef | None = None
    department: ActorRef | None = None
    service: ActorRef | None = None
    sla_days: int | None = None
    routing_rule_code: str | None = None
    routing_rule_id: int | None = None
    escalation_path: list[EscalationStepRef] = Field(default_factory=list)

    # Outcome detail.
    conflict_rule_codes: list[str] = Field(default_factory=list)
    explanation: str | None = None
    reason: str | None = None
    audit_id: int | None = None


class IssueTypeSummary(BaseModel):
    code: str
    name: str
    category: str
    description: str | None = None
    is_active: bool


class IssueTypeListResponse(BaseModel):
    count: int
    issue_types: list[IssueTypeSummary]


class RoutingRuleSummary(BaseModel):
    id: int
    code: str
    issue_type_code: str
    scope: str
    priority: int
    rationale: str
    effective_from: date
    effective_to: date | None = None
    authority_code: str
    authority_name: str
    department_code: str
    department_name: str
    service_code: str
    service_name: str
    jurisdiction_code: str | None = None
    active_on: date | None = None


class RoutingRuleListResponse(BaseModel):
    count: int
    active_on: date | None = None
    issue_type: str | None = None
    rules: list[RoutingRuleSummary]