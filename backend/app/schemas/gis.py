"""Pydantic schemas for the GIS + temporal jurisdiction API (P1).

All coordinates follow GeoJSON convention: (longitude, latitude); WGS84
(EPSG:4326) is the exchange CRS. Metric values (area/length) are computed in
UTM zone 43N (EPSG:32643) via the CRS module.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.gis.crs import CRS_UTM_43N, CRS_WGS84


class LookupStatus(str, Enum):
    """Outcome codes produced by the temporal jurisdiction engine."""

    MATCHED = "MATCHED"
    NO_JURISDICTION = "NO_JURISDICTION"
    INVALID_COORDINATES = "INVALID_COORDINATES"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    TEMPORAL_CONFLICT = "TEMPORAL_CONFLICT"


class AuthorityRef(BaseModel):
    id: int
    code: str
    name: str


class JurisdictionVersionRef(BaseModel):
    id: int
    version_no: int
    code: str
    name: str
    status: str
    effective_from: date
    effective_to: date | None = None


class JurisdictionRef(BaseModel):
    id: int
    code: str
    name: str
    kind: str
    authority: AuthorityRef | None = None
    version: JurisdictionVersionRef | None = None


class WardRef(BaseModel):
    id: int
    ward_code: str
    name: str
    locality: str | None = None
    jurisdiction_id: int


class AreaRef(BaseModel):
    id: int
    code: str
    name: str
    ward_code: str
    jurisdiction_id: int


class CorridorRef(BaseModel):
    id: int
    code: str
    name: str
    road_class: str
    jurisdiction_id: int


class JurisdictionLookupRequest(BaseModel):
    lat: float = Field(ge=-90.0, le=90.0, description="Latitude in WGS84 degrees")
    lng: float = Field(ge=-180.0, le=180.0, description="Longitude in WGS84 degrees")
    on_date: date = Field(default_factory=date.today, description="Temporal point of the query")


class JurisdictionLookupResult(BaseModel):
    status: LookupStatus
    on_date: date
    lat: float
    lng: float
    jurisdiction: JurisdictionRef | None = None
    version: JurisdictionVersionRef | None = None
    ward: WardRef | None = None
    areas: list[AreaRef] = Field(default_factory=list)
    corridor: CorridorRef | None = None
    service_responsibility: Literal["NOT_EVALUATED"] = "NOT_EVALUATED"
    message: str | None = None


class JurisdictionSummary(BaseModel):
    id: int
    code: str
    name: str
    kind: str
    authority_code: str
    version_code: str
    version_status: str
    effective_from: date
    effective_to: date | None = None
    superseded_by_code: str | None = None
    geometry_geojson: dict | None = None


class JurisdictionDetail(JurisdictionSummary):
    superseded_by_id: int | None = None
    parent_jurisdiction_id: int | None = None
    parent_jurisdiction_code: str | None = None
    notes: str | None = None
    envelope_geojson: dict | None = None


class JurisdictionListResponse(BaseModel):
    count: int
    on_date: date | None = None
    version_id: int | None = None
    kind: str | None = None
    include_geometry: bool = False
    jurisdictions: list[JurisdictionSummary]


class JurisdictionVersionHistoryEntry(BaseModel):
    jurisdiction_id: int
    version: JurisdictionVersionRef
    effective_from: date
    effective_to: date | None = None
    superseded_by_id: int | None = None


class JurisdictionVersionHistory(BaseModel):
    code: str
    name: str
    count: int
    entries: list[JurisdictionVersionHistoryEntry]


class WardSummary(BaseModel):
    id: int
    ward_code: str
    name: str
    locality: str | None = None
    jurisdiction_id: int
    jurisdiction_code: str


class WardListResponse(BaseModel):
    count: int
    wards: list[WardSummary]


class AreaSummary(BaseModel):
    id: int
    code: str
    name: str
    ward_code: str
    ward_name: str
    description: str | None = None
    geometry_geojson: dict | None = None


class AreaListResponse(BaseModel):
    count: int
    areas: list[AreaSummary]


class RoadSummary(BaseModel):
    id: int
    code: str
    name: str
    road_class: str
    jurisdiction_code: str
    geometry_geojson: dict | None = None


class RoadListResponse(BaseModel):
    count: int
    roads: list[RoadSummary]


class GeometryValidationRequest(BaseModel):
    geometry: dict
    repair: bool = False


class GeometryValidationResult(BaseModel):
    valid: bool
    geometry_type: str | None = None
    reason: str | None = None
    repair: "GeometryRepairResult | None" = None


class GeometryRepairRequest(BaseModel):
    geometry: dict


class GeometryRepairResult(BaseModel):
    required: bool
    was_changed: bool
    geometry_type: str | None = None
    report: list[str] = Field(default_factory=list)
    geometry: dict | None = None


class BoundsRef(BaseModel):
    minx: float
    miny: float
    maxx: float
    maxy: float


class GeometryDescribeRequest(BaseModel):
    geometry: dict


class GeometryDescribeResult(BaseModel):
    geometry_type: str
    is_valid: bool
    is_empty: bool
    parts: int
    area_km2: float | None = None
    length_km: float | None = None
    bounds: BoundsRef | None = None
    centroid: dict[str, float] | None = None
    crs: str = CRS_UTM_43N


class SpatialOperationRequest(BaseModel):
    operation: Literal["intersection", "difference", "union", "contains", "intersects", "within"]
    a: dict
    b: dict


class SpatialOperationResult(BaseModel):
    operation: str
    result: dict | None = None
    result_type: str | None = None
    value: bool | None = None
    warnings: list[str] = Field(default_factory=list)


class TransformRequest(BaseModel):
    geometry: dict
    from_crs: str = CRS_WGS84
    to_crs: str = CRS_UTM_43N


class TransformResult(BaseModel):
    geometry: dict
    crs: str


class TemporalOverlapReport(BaseModel):
    kind: str
    code: str
    count: int
    jurisdiction_ids: list[int]
    version_ids: list[int]
    effective_windows: list[dict] = Field(default_factory=list)