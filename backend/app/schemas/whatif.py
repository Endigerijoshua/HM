"""Pydantic schemas for the What-If jurisdiction simulator (P3).

The simulator is strictly read/create/calculate/display: it builds proposed
boundaries isolated from the live ``jurisdictions`` table and reports every
delta (area, wards, roads, complaints, responsibility) without mutating a single
live row. A scenario may only ever be *applied* through the explicit migration
flow in a later phase.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.routing import RoutingResult


class ScenarioStatus(str, Enum):
    DRAFT = "DRAFT"
    SIMULATED = "SIMULATED"
    APPLIED = "APPLIED"
    DISCARDED = "DISCARDED"


class ImpactMetric(BaseModel):
    label: str
    current: float
    proposed: float
    delta: float


class ResponsibilityDelta(BaseModel):
    issue_type_code: str
    issue_type_name: str
    longitude: float
    latitude: float
    on_date: date
    status: str
    matched_scope: str | None = None
    authority_code: str | None = None
    authority_name: str | None = None
    department_code: str | None = None
    department_name: str | None = None
    service_code: str | None = None
    service_name: str | None = None
    routing_rule_code: str | None = None
    conflict_rule_codes: list[str] = Field(default_factory=list)
    description: str


class MaybeRemovedJurisdiction(BaseModel):
    code: str
    name: str
    kind: str
    area_km2: float


class ComplaintSnapshot(BaseModel):
    public_ref: str
    issue_type_code: str
    ward_code: str | None = None
    authority_code: str | None = None
    department_code: str | None = None
    service_code: str | None = None
    proposed_authority_code: str | None = None
    proposed_department_code: str | None = None
    proposed_service_code: str | None = None
    responsibility_changes: bool


class WhatIfComplaintRef(BaseModel):
    public_ref: str
    issue_type_code: str
    latitude: float
    longitude: float
    ward_code: str | None = None
    ward_name: str | None = None


class WhatIfScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    status: ScenarioStatus
    applies_to: str | None = None
    affected_region_name: str | None = None
    geometry_geojson: dict | None = None
    envelope_geojson: dict | None = None
    result_summary: dict | None = None
    created_at: str


class WhatIfScenarioListResponse(BaseModel):
    count: int
    scenarios: list[WhatIfScenarioResponse]


class WhatIfScenarioCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    status: ScenarioStatus = ScenarioStatus.DRAFT
    applies_to: str | None = None
    affected_region_name: str | None = None
    geometry_geojson: dict = Field(description="Proposed boundary as GeoJSON geometry")


class WhatIfSimulateRequest(BaseModel):
    longitude: float = Field(ge=-180.0, le=180.0)
    latitude: float = Field(ge=-90.0, le=90.0)
    issue_type_code: str = Field(min_length=1)
    on_date: date = Field(default_factory=date.today)


class WhatIfSimulateResponse(BaseModel):
    scenario_code: str
    scenario_name: str
    in_proposed_geometry: bool
    on_date: date
    current: RoutingResult
    proposed: RoutingResult | None = None
    responsibility_deltas: list[ResponsibilityDelta] = Field(default_factory=list)
    affected_complaint_count: int
    impact: list[ImpactMetric] = Field(default_factory=list)
    potential_conflicts: list[str] = Field(default_factory=list)


class WhatIfImpactResponse(BaseModel):
    scenario_code: str
    scenario_name: str
    affected_complaints: list[WhatIfComplaintRef]
    impact: list[ImpactMetric]
    potential_conflicts: list[str]


class MigrationComplaintPreview(BaseModel):
    """Per-complaint before/after responsibility for the migration preview (P4)."""

    complaint_id: int
    public_ref: str
    issue_type: str
    issue_type_name: str | None = None
    latitude: float
    longitude: float
    status: str
    in_proposed_boundary: bool
    current_jurisdiction_code: str | None = None
    current_jurisdiction_name: str | None = None
    current_ward_code: str | None = None
    current_ward_name: str | None = None
    current_authority_code: str | None = None
    current_authority_name: str | None = None
    current_department_code: str | None = None
    current_department_name: str | None = None
    current_service_code: str | None = None
    current_service_name: str | None = None
    proposed_jurisdiction_code: str | None = None
    proposed_jurisdiction_name: str | None = None
    proposed_ward_code: str | None = None
    proposed_ward_name: str | None = None
    proposed_authority_code: str | None = None
    proposed_authority_name: str | None = None
    proposed_department_code: str | None = None
    proposed_department_name: str | None = None
    proposed_service_code: str | None = None
    proposed_service_name: str | None = None
    migration_required: bool
    explanation: str


class MigrationPreviewResponse(BaseModel):
    """Read-only migration preview for a proposed boundary (P4)."""

    scenario_code: str
    scenario_name: str
    preview_date: date
    total_open_complaints: int
    affected_count: int
    complaints: list[MigrationComplaintPreview] = Field(default_factory=list)
