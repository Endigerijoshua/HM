"""GIS + temporal jurisdiction API (P1).

Endpoints
---------
* ``GET  /gis/jurisdictions``                 - list/filter jurisdictions
* ``GET  /gis/jurisdictions/{id}``            - single jurisdiction detail
* ``GET  /gis/jurisdictions/{id}/versions``   - version history for a code
* ``POST /gis/lookup``                        - temporal point lookup
* ``POST /gis/validate-geometry``             - geometry validation (+ optional repair)
* ``POST /gis/repair-geometry``               - controlled geometry repair with report
* ``POST /gis/describe``                      - geometry analysis (area/bounds/centroid)
* ``POST /gis/operations``                    - spatial algebra (predicates + set ops)
* ``POST /gis/transform``                     - CRS reprojection
* ``GET  /gis/wards``                         - ward lookups
* ``GET  /gis/areas``                         - area lookups
* ``GET  /gis/roads``                         - road corridor lookups

Service responsibility is intentionally NOT resolved here (P1 scope): lookups
answer *geographic containment* only, and every result carries
``service_responsibility: "NOT_EVALUATED"``.
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_gis_service,
    get_temporal_engine,
)
from app.core.errors import NotFoundError
from app.db.models.jurisdiction import Area, Jurisdiction, Road, Ward
from app.gis.base import sort_jurisdictions
from app.gis.ops import GisService
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.schemas.gis import (
    AreaListResponse,
    AreaSummary,
    GeometryDescribeRequest,
    GeometryDescribeResult,
    GeometryRepairRequest,
    GeometryRepairResult,
    GeometryValidationRequest,
    GeometryValidationResult,
    JurisdictionDetail,
    JurisdictionListResponse,
    JurisdictionLookupRequest,
    JurisdictionLookupResult,
    JurisdictionSummary,
    JurisdictionVersionHistory,
    JurisdictionVersionHistoryEntry,
    JurisdictionVersionRef,
    RoadListResponse,
    RoadSummary,
    SpatialOperationRequest,
    SpatialOperationResult,
    TransformRequest,
    TransformResult,
    WardListResponse,
    WardSummary,
)

router = APIRouter(prefix="/gis", tags=["gis"])


# ----------------------------------------------------------------------
# jurisdiction endpoints
# ----------------------------------------------------------------------


@router.get(
    "/jurisdictions",
    response_model=JurisdictionListResponse,
    summary="List jurisdictions, optionally temporally or by kind/version",
)
def list_jurisdictions(
    date: date | None = Query(None, alias="date", description="Only show jurisdictions in force on this date"),
    version_id: int | None = Query(None, description="Only show jurisdictions of this boundary version"),
    kind: str | None = Query(None, description="Only show jurisdictions of this kind (WARD, AREA, ...)"),
    include_geometry: bool = Query(False, description="Include GeoJSON geometry in each item"),
    db: Session = Depends(get_db),
) -> JurisdictionListResponse:
    stmt = select(Jurisdiction)
    if date is not None:
        stmt = stmt.where(
            Jurisdiction.effective_from <= date,
            or_(Jurisdiction.effective_to.is_(None), date < Jurisdiction.effective_to),
        )
    if version_id is not None:
        stmt = stmt.where(Jurisdiction.jurisdiction_version_id == version_id)
    if kind is not None:
        stmt = stmt.where(Jurisdiction.kind == kind)

    rows = sort_jurisdictions(list(db.scalars(stmt)))
    items = [_summary(row, include_geometry=include_geometry) for row in rows]
    return JurisdictionListResponse(
        count=len(items),
        on_date=date,
        version_id=version_id,
        kind=kind,
        include_geometry=include_geometry,
        jurisdictions=items,
    )


@router.get(
    "/jurisdictions/{jurisdiction_id}",
    response_model=JurisdictionDetail,
    summary="Single jurisdiction with geometry",
)
def get_jurisdiction(
    jurisdiction_id: int,
    date: date | None = Query(None, alias="date", description="404 if jurisdiction not in force on this date"),
    include_geometry: bool = Query(True),
    db: Session = Depends(get_db),
) -> JurisdictionDetail:
    jurisdiction = db.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise NotFoundError(f"Jurisdiction {jurisdiction_id} not found")

    if date is not None:
        active = (
            jurisdiction.effective_from <= date
            and (jurisdiction.effective_to is None or date < jurisdiction.effective_to)
        )
        if not active:
            raise NotFoundError(
                f"Jurisdiction {jurisdiction.code} was not in force on {date.isoformat()}"
            )

    return _summary(jurisdiction, include_geometry=include_geometry, detail=True)


@router.get(
    "/jurisdictions/{jurisdiction_id}/versions",
    response_model=JurisdictionVersionHistory,
    summary="Version history for a jurisdiction code",
)
def jurisdiction_versions(
    jurisdiction_id: int,
    db: Session = Depends(get_db),
) -> JurisdictionVersionHistory:
    jurisdiction = db.get(Jurisdiction, jurisdiction_id)
    if jurisdiction is None:
        raise NotFoundError(f"Jurisdiction {jurisdiction_id} not found")

    rows = (
        db.query(Jurisdiction)
        .filter(Jurisdiction.code == jurisdiction.code)
        .order_by(Jurisdiction.effective_from, Jurisdiction.id)
        .all()
    )
    entries = []
    for row in rows:
        version = row.version
        entries.append(
            JurisdictionVersionHistoryEntry(
                jurisdiction_id=row.id,
                version=JurisdictionVersionRef(
                    id=version.id,
                    version_no=version.version_no,
                    code=version.code,
                    name=version.name,
                    status=version.status,
                    effective_from=version.effective_from,
                    effective_to=version.effective_to,
                ),
                effective_from=row.effective_from,
                effective_to=row.effective_to,
                superseded_by_id=row.superseded_by_id,
            )
        )
    return JurisdictionVersionHistory(
        code=jurisdiction.code,
        name=jurisdiction.name,
        count=len(entries),
        entries=entries,
    )


# ----------------------------------------------------------------------
# lookup endpoint
# ----------------------------------------------------------------------


@router.post(
    "/lookup",
    response_model=JurisdictionLookupResult,
    summary="Temporal jurisdiction lookup for a point + date",
)
def lookup_jurisdiction(
    request: JurisdictionLookupRequest,
    engine: TemporalJurisdictionEngine = Depends(get_temporal_engine),
) -> JurisdictionLookupResult:
    return engine.resolve_jurisdiction_at_point(request.lng, request.lat, request.on_date)


# ----------------------------------------------------------------------
# geometry endpoints
# ----------------------------------------------------------------------


@router.post(
    "/validate-geometry",
    response_model=GeometryValidationResult,
    summary="Validate a GeoJSON geometry (optionally repair)",
)
def validate_geometry(
    request: GeometryValidationRequest,
    service: GisService = Depends(get_gis_service),
) -> GeometryValidationResult:
    return service.validate(request.geometry, repair=request.repair)


@router.post(
    "/repair-geometry",
    response_model=GeometryRepairResult,
    summary="Repair an invalid geometry and report what changed",
)
def repair_geometry(
    request: GeometryRepairRequest,
    service: GisService = Depends(get_gis_service),
) -> GeometryRepairResult:
    return service.repair(request.geometry)


@router.post(
    "/describe",
    response_model=GeometryDescribeResult,
    summary="Describe a geometry (type, area, bounds, centroid)",
)
def describe_geometry(
    request: GeometryDescribeRequest,
    service: GisService = Depends(get_gis_service),
) -> GeometryDescribeResult:
    return service.describe(request.geometry)


@router.post(
    "/operations",
    response_model=SpatialOperationResult,
    summary="Run a spatial predicate or set operation",
)
def spatial_operations(
    request: SpatialOperationRequest,
    service: GisService = Depends(get_gis_service),
) -> SpatialOperationResult:
    return service.operate(request.operation, request.a, request.b)


@router.post(
    "/transform",
    response_model=TransformResult,
    summary="Reproject a GeoJSON geometry between CRSs",
)
def transform_geometry(
    request: TransformRequest,
    service: GisService = Depends(get_gis_service),
) -> TransformResult:
    return service.transform(request.geometry, request.from_crs, request.to_crs)


# ----------------------------------------------------------------------
# ward / area / road lookups
# ----------------------------------------------------------------------


@router.get("/wards", response_model=WardListResponse, summary="List wards")
def list_wards(
    db: Session = Depends(get_db),
) -> WardListResponse:
    rows = db.query(Ward).order_by(Ward.ward_code).all()
    items = []
    for ward in rows:
        jurisdiction = ward.jurisdiction
        items.append(
            WardSummary(
                id=ward.id,
                ward_code=ward.ward_code,
                name=ward.name,
                locality=ward.locality,
                jurisdiction_id=ward.jurisdiction_id,
                jurisdiction_code=jurisdiction.code if jurisdiction else "",
            )
        )
    return WardListResponse(count=len(items), wards=items)


@router.get("/areas", response_model=AreaListResponse, summary="List areas")
def list_areas(
    db: Session = Depends(get_db),
) -> AreaListResponse:
    rows = db.query(Area).order_by(Area.code).all()
    items = []
    for area in rows:
        ward = area.ward
        items.append(
            AreaSummary(
                id=area.id,
                code=area.code,
                name=area.name,
                ward_code=ward.ward_code if ward else "",
                ward_name=ward.name if ward else "",
                description=area.description,
                geometry_geojson=json.loads(area.geometry_geojson),
            )
        )
    return AreaListResponse(count=len(items), areas=items)


@router.get("/roads", response_model=RoadListResponse, summary="List road corridors")
def list_roads(
    db: Session = Depends(get_db),
) -> RoadListResponse:
    rows = db.query(Road).order_by(Road.code).all()
    items = []
    for road in rows:
        jurisdiction = road.jurisdiction
        items.append(
            RoadSummary(
                id=road.id,
                code=road.code,
                name=road.name,
                road_class=road.road_class,
                jurisdiction_code=jurisdiction.code if jurisdiction else "",
                geometry_geojson=json.loads(road.geometry_geojson),
            )
        )
    return RoadListResponse(count=len(items), roads=items)


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------


def _summary(
    row: Jurisdiction,
    *,
    include_geometry: bool = False,
    detail: bool = False,
):
    superseded = row.superseded_by
    parent = row.parent_jurisdiction
    common = {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "kind": row.kind,
        "authority_code": row.authority.code if row.authority else "",
        "version_code": row.version.code if row.version else "",
        "version_status": row.version.status if row.version else "",
        "effective_from": row.effective_from,
        "effective_to": row.effective_to,
        "superseded_by_code": superseded.code if superseded else None,
    }
    if not detail:
        if include_geometry:
            common["geometry_geojson"] = json.loads(row.geometry_geojson)
        return JurisdictionSummary(**common)
    return JurisdictionDetail(
        **common,
        superseded_by_id=row.superseded_by_id,
        parent_jurisdiction_id=row.parent_jurisdiction_id,
        parent_jurisdiction_code=parent.code if parent else None,
        notes=row.notes,
        geometry_geojson=json.loads(row.geometry_geojson) if include_geometry else None,
        envelope_geojson=json.loads(row.envelope_geojson) if include_geometry else None,
    )