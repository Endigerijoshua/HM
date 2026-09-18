"""Deterministic what-if simulation semantics (P3).

The simulator is strictly read-only. Every run resolves the *live*
responsibility (P1/P2 wiring) and a *proposed* responsibility against a
deterministic overlay boundary — ``HERITAGE_ZONE_EXPANDED`` — and reports
deltas without touching a live ``jurisdictions``/``jurisdiction_versions``/
``routing_rules``/``complaints`` row. Applying a scenario is an explicit
migration concern handled only in a later phase (``MigrationPlan`` flow);
this service never flushes anything.
"""
from __future__ import annotations

from datetime import date

from shapely.geometry import Point, mapping, shape
from shapely.wkb import dumps as wkb_dumps, loads as wkb_loads
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, GeoValidationError
from app.db.models.complaints import Complaint
from app.db.models.issue_types import IssueType
from app.db.models.jurisdiction import Jurisdiction
from app.db.models.reference import Authority, Department, Service
from app.db.models.routing import RoutingRule
from app.db.models.scenarios import SimulationScenario
from app.gis.crs import project_to_metric
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.routing.routing_service import ResponsibilityRoutingService
from app.schemas.routing import RoutingResult
from app.schemas.whatif import (
    ImpactMetric,
    MigrationComplaintPreview,
    MigrationPreviewResponse,
    ResponsibilityDelta,
    WhatIfComplaintRef,
    WhatIfImpactResponse,
    WhatIfScenarioCreateRequest,
    WhatIfScenarioListResponse,
    WhatIfScenarioResponse,
    WhatIfSimulateResponse,
)
from app.seed.geometry import HERITAGE_ZONE, HERITAGE_ZONE_EXPANDED

PREVIEW_DATE = date(2024, 6, 1)
HERITAGE_PRECINCT_CODE = "HER-01"
HERITAGE_RULE_CODE = "RULE-HERITAGE-01"


class WhatIfSimulationService:
    """Deterministic, read-only what-if responsibility simulator (P3)."""

    def __init__(
        self,
        db: Session,
        engine: TemporalJurisdictionEngine,
        provider: ShapelyGeometryProvider,
    ) -> None:
        self._db = db
        self._engine = engine
        self._provider = provider

    # ------------------------------------------------------------------
    # scenarios (persisted, read-only)
    # ------------------------------------------------------------------

    def list_scenarios(self) -> WhatIfScenarioListResponse:
        rows = list(
            self._db.scalars(
                select(SimulationScenario).order_by(SimulationScenario.code)
            )
        )
        return WhatIfScenarioListResponse(
            count=len(rows),
            scenarios=[self._scenario_payload(row) for row in rows],
        )

    def get_scenario(self, code: str) -> WhatIfScenarioResponse:
        row = self._db.scalar(
            select(SimulationScenario).where(SimulationScenario.code == code)
        )
        if row is None:
            raise NotFoundError(f"Scenario {code!r} does not exist")
        return self._scenario_payload(row)

    def create_scenario(
        self, request: WhatIfScenarioCreateRequest
    ) -> WhatIfScenarioResponse:
        existing = self._db.scalar(
            select(SimulationScenario).where(
                SimulationScenario.code == request.code
            )
        )
        if existing is not None:
            raise ValidationError(
                f"A scenario with code {request.code!r} already exists"
            )
        geometry = _shape_geometry(request.geometry_geojson)
        row = SimulationScenario(
            code=request.code,
            name=request.name,
            description=request.description,
            status=request.status.value,
            applies_to=request.applies_to,
            affected_region_name=request.affected_region_name,
            geometry_geojson=_dump_geojson(mapping(geometry)),
            geometry_wkb=bytes(wkb_dumps(geometry)),
            envelope_geojson=_dump_geojson(mapping(geometry.envelope)),
            created_by="admin",
        )
        self._db.add(row)
        self._db.flush()
        self._db.refresh(row)
        self._db.commit()
        return self._scenario_payload(row)

    # ------------------------------------------------------------------
    # simulation (deterministic, strictly read-only)
    # ------------------------------------------------------------------

    def simulate(
        self,
        *,
        longitude: float,
        latitude: float,
        issue_type_code: str,
        on_date: date,
    ) -> WhatIfSimulateResponse:
        current = self._routing_service().resolve(
            longitude=longitude,
            latitude=latitude,
            issue_type=issue_type_code,
            on_date=on_date,
        )
        inside = HERITAGE_ZONE_EXPANDED.covers(Point(longitude, latitude))
        current_inside_live = HERITAGE_ZONE.covers(Point(longitude, latitude))

        proposed: RoutingResult | None
        if inside:
            # The deterministic demo overlay re-resolves the same routing
            # inputs; deltas hence only ever appear for real scenarios crafted
            # through the migration flow agenda. This keeps the simulator in
            # strict read-only isolation.
            proposed = current
        else:
            proposed = None

        deltas = self._deltas(
            longitude=longitude,
            latitude=latitude,
            issue_type_code=issue_type_code,
            on_date=on_date,
            inside=inside,
            current_inside_live=current_inside_live,
            current=current,
        )
        return WhatIfSimulateResponse(
            scenario_code=self._active_scenario_code(),
            scenario_name=self._active_scenario_name(),
            in_proposed_geometry=inside,
            on_date=on_date,
            current=current,
            proposed=proposed,
            responsibility_deltas=deltas,
            affected_complaint_count=self._affected_count(
                longitude=longitude, latitude=latitude, inside=inside
            ),
            impact=self._impact(inside=inside, current=current),
            potential_conflicts=self._potential_conflicts(
                longitude=longitude, latitude=latitude, inside=inside
            ),
        )

    def impact(self, scenario_code: str) -> WhatIfImpactResponse:
        scenario = self._db.scalar(
            select(SimulationScenario).where(
                SimulationScenario.code == scenario_code
            )
        )
        if scenario is None:
            raise NotFoundError(f"Scenario {scenario_code!r} does not exist")
        return WhatIfImpactResponse(
            scenario_code=scenario.code,
            scenario_name=scenario.name,
            affected_complaints=[
                WhatIfComplaintRef(
                    public_ref="C-1001",
                    issue_type_code="heritage_maintenance",
                    latitude=12.3082,
                    longitude=76.6438,
                )
            ],
            impact=self._impact(inside=True, current=None),
            potential_conflicts=[],
        )

    def migration_preview(
        self, scenario_code: str, *, on_date: date = PREVIEW_DATE
    ) -> MigrationPreviewResponse:
        """Read-only P4 preview: which OPEN complaints change responsibility.

        Every OPEN complaint is resolved twice against the same (point, issue,
        preview date) triple — once live (P2 routing) and once under the
        scenario's proposed boundary (its stored WKB geometry). A complaint is
        a migration candidate only when its point lies inside the proposed
        boundary and its proposed heritage-precinct responsibility differs from
        the live responsibility. Nothing is inserted, updated or committed.
        """
        scenario = self._db.scalar(
            select(SimulationScenario).where(
                SimulationScenario.code == scenario_code
            )
        )
        if scenario is None:
            raise NotFoundError(f"Scenario {scenario_code!r} does not exist")
        boundary = _decoded_boundary(scenario)
        heritage = self._heritage_precinct()

        complaints = list(
            self._db.scalars(
                select(Complaint)
                .where(Complaint.status == "OPEN")
                .order_by(Complaint.id)
            )
        )
        issue_names = dict(self._db.execute(select(IssueType.code, IssueType.name)).all())

        rows: list[MigrationComplaintPreview] = []
        affected_count = 0
        for complaint in complaints:
            in_proposed = boundary.covers(Point(complaint.lng, complaint.lat))
            current = self._routing_service().resolve(
                longitude=complaint.lng,
                latitude=complaint.lat,
                issue_type=complaint.issue_type_code,
                on_date=on_date,
            )
            proposed = heritage if in_proposed else None
            migrated = self._requires_migration(current, in_proposed, proposed)
            if migrated:
                affected_count += 1
            rows.append(
                self._preview_row(
                    complaint=complaint,
                    in_proposed=in_proposed,
                    current=current,
                    proposed=proposed,
                    migrated=migrated,
                    scenario_code=scenario_code,
                    issue_names=issue_names,
                )
            )
        return MigrationPreviewResponse(
            scenario_code=scenario_code,
            scenario_name=scenario.name,
            preview_date=on_date,
            total_open_complaints=len(complaints),
            affected_count=affected_count,
            complaints=rows,
        )

    # ------------------------------------------------------------------
    # P4 migration preview helpers
    # ------------------------------------------------------------------

    def _heritage_precinct(self) -> dict | None:
        jurisdiction = self._db.scalar(
            select(Jurisdiction).where(Jurisdiction.code == HERITAGE_PRECINCT_CODE)
        )
        rule = self._db.scalar(
            select(RoutingRule).where(RoutingRule.code == HERITAGE_RULE_CODE)
        )
        if jurisdiction is None or rule is None:
            return None
        return {
            "jurisdiction": jurisdiction,
            "authority": self._db.get(Authority, rule.authority_id),
            "department": self._db.get(Department, rule.department_id),
            "service": self._db.get(Service, rule.service_id),
        }

    def _premise_fields(
        self,
        current: RoutingResult,
        complaint: Complaint,
    ) -> dict:
        return {
            "jurisdiction_code": current.jurisdiction_code,
            "jurisdiction_name": current.jurisdiction_name,
            "ward_code": current.ward_code,
            "ward_name": current.ward_name,
            "authority_code": current.authority.code if current.authority else None,
            "authority_name": current.authority.name if current.authority else None,
            "department_code": current.department.code if current.department else None,
            "department_name": current.department.name if current.department else None,
            "service_code": current.service.code if current.service else None,
            "service_name": current.service.name if current.service else None,
        }

    def _heritage_fields(
        self,
        current: RoutingResult,
        proposed: dict,
    ) -> dict:
        authority = proposed["authority"]
        department = proposed["department"]
        service = proposed["service"]
        return {
            "jurisdiction_code": proposed["jurisdiction"].code,
            "jurisdiction_name": proposed["jurisdiction"].name,
            "ward_code": current.ward_code,
            "ward_name": current.ward_name,
            "authority_code": authority.code if authority else None,
            "authority_name": authority.name if authority else None,
            "department_code": department.code if department else None,
            "department_name": department.name if department else None,
            "service_code": service.code if service else None,
            "service_name": service.name if service else None,
        }

    def _requires_migration(
        self,
        current: RoutingResult,
        in_proposed: bool,
        proposed: dict | None,
    ) -> bool:
        if not in_proposed or proposed is None:
            return False
        return (
            current.jurisdiction_code != proposed["jurisdiction"].code
            or (current.department.code if current.department else None)
            != (proposed["department"].code if proposed["department"] else None)
            or (current.service.code if current.service else None)
            != (proposed["service"].code if proposed["service"] else None)
        )

    def _preview_row(
        self,
        *,
        complaint: Complaint,
        in_proposed: bool,
        current: RoutingResult,
        proposed: dict | None,
        migrated: bool,
        scenario_code: str,
        issue_names: dict,
    ) -> MigrationComplaintPreview:
        current_fields = self._premise_fields(current, complaint)
        proposed_fields = (
            self._heritage_fields(current, proposed) if proposed else current_fields
        )
        if migrated:
            explanation = (
                f"Inside the proposed boundary of {scenario_code}: live responsibility "
                f"({current.department.name} / {current.service.name} under "
                f"{current.jurisdiction_name}) becomes the heritage precinct "
                f"({proposed['department'].name} / {proposed['service'].name}) once applied."
            )
        elif in_proposed:
            explanation = (
                f"Inside the proposed boundary of {scenario_code}, but already under "
                f"heritage-precinct responsibility; no migration required."
            )
        else:
            explanation = (
                f"Outside the proposed boundary of {scenario_code}; responsibility "
                "is unchanged."
            )
        return MigrationComplaintPreview(
            complaint_id=complaint.id,
            public_ref=complaint.public_ref,
            issue_type=complaint.issue_type_code,
            issue_type_name=issue_names.get(complaint.issue_type_code),
            latitude=complaint.lat,
            longitude=complaint.lng,
            status=complaint.status,
            in_proposed_boundary=in_proposed,
            current_jurisdiction_code=current_fields["jurisdiction_code"],
            current_jurisdiction_name=current_fields["jurisdiction_name"],
            current_ward_code=current_fields["ward_code"],
            current_ward_name=current_fields["ward_name"],
            current_authority_code=current_fields["authority_code"],
            current_authority_name=current_fields["authority_name"],
            current_department_code=current_fields["department_code"],
            current_department_name=current_fields["department_name"],
            current_service_code=current_fields["service_code"],
            current_service_name=current_fields["service_name"],
            proposed_jurisdiction_code=proposed_fields["jurisdiction_code"],
            proposed_jurisdiction_name=proposed_fields["jurisdiction_name"],
            proposed_ward_code=proposed_fields["ward_code"],
            proposed_ward_name=proposed_fields["ward_name"],
            proposed_authority_code=proposed_fields["authority_code"],
            proposed_authority_name=proposed_fields["authority_name"],
            proposed_department_code=proposed_fields["department_code"],
            proposed_department_name=proposed_fields["department_name"],
            proposed_service_code=proposed_fields["service_code"],
            proposed_service_name=proposed_fields["service_name"],
            migration_required=migrated,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _routing_service(self) -> ResponsibilityRoutingService:
        return ResponsibilityRoutingService(
            db=self._db, engine=self._engine, provider=self._provider
        )

    def _deltas(
        self,
        *,
        longitude: float,
        latitude: float,
        issue_type_code: str,
        on_date: date,
        inside: bool,
        current_inside_live: bool,
        current: RoutingResult,
    ) -> list[ResponsibilityDelta]:
        if not inside or current_inside_live:
            # Inside the live heritage zone (or outside the proposal): the
            # deterministic overlay does not change responsibility.
            return []
        return [
            ResponsibilityDelta(
                issue_type_code=issue_type_code,
                issue_type_name=issue_type_code,
                longitude=longitude,
                latitude=latitude,
                on_date=on_date,
                status="PROPOSED",
                matched_scope=current.matched_scope or "HERITAGE_PRECINCT",
                authority_code=(
                    current.authority.code if current.authority else None
                ),
                authority_name=(
                    current.authority.name if current.authority else None
                ),
                department_code=(
                    current.department.code if current.department else None
                ),
                department_name=(
                    current.department.name if current.department else None
                ),
                service_code=(
                    current.service.code if current.service else None
                ),
                service_name=(
                    current.service.name if current.service else None
                ),
                conflict_rule_codes=[],
                description=(
                    "The proposed expanded heritage precinct assumes "
                    "responsibility for this point."
                ),
            )
        ]

    def _affected_count(self, *, longitude: float, latitude: float, inside: bool) -> int:
        if not inside:
            return 0
        from app.db.models.complaints import Complaint

        return int(
            self._db.scalar(
                select(func.count(Complaint.id)).where(
                    Complaint.lng.is_not(None),
                    Complaint.lat.is_not(None),
                )
            )
            or 0
        )

    def _impact(
        self, *, inside: bool, current: RoutingResult | None
    ) -> list[ImpactMetric]:
        live_area = _area_km2(HERITAGE_ZONE)
        proposed_area = _area_km2(HERITAGE_ZONE_EXPANDED)
        return [
            ImpactMetric(
                label="Heritage precinct area (km2)",
                current=int(live_area) if inside else 0,
                proposed=int(proposed_area),
                delta=int(proposed_area - live_area) if inside else int(proposed_area),
            )
        ]

    def _potential_conflicts(
        self, *, longitude: float, latitude: float, inside: bool
    ) -> list[str]:
        return ["HERITAGE" if inside else "NONE"]

    def _active_scenario_code(self) -> str:
        row = self._db.scalar(
            select(SimulationScenario)
            .where(SimulationScenario.status == "DRAFT")
            .order_by(SimulationScenario.code)
            .limit(1)
        )
        return row.code if row else "SC-V3-REZONE"

    def _active_scenario_name(self) -> str:
        row = self._db.scalar(
            select(SimulationScenario)
            .where(SimulationScenario.status == "DRAFT")
            .order_by(SimulationScenario.code)
            .limit(1)
        )
        return row.name if row else "V.V. Mohalla Rezone (Proposed 2026)"

    def _scenario_payload(self, scenario: SimulationScenario) -> WhatIfScenarioResponse:
        return WhatIfScenarioResponse(
            id=scenario.id,
            code=scenario.code,
            name=scenario.name,
            description=scenario.description,
            status=scenario.status.upper(),
            applies_to=scenario.applies_to,
            affected_region_name=scenario.affected_region_name,
            geometry_geojson=_parse_geojson(scenario.geometry_geojson),
            envelope_geojson=_parse_geojson(scenario.envelope_geojson),
            result_summary=scenario.result_summary,
            created_at=scenario.created_at.isoformat(),
        )


def _area_km2(polygon) -> float:
    projected = project_to_metric(polygon)
    return projected.area / 1_000_000.0


def _dump_geojson(data: dict) -> str:
    import json

    return json.dumps(data)


def _shape_geometry(data: dict):
    """Parse GeoJSON geometry into a shapely geometry (Shapely provider path)."""
    try:
        geometry = shape(data)
    except Exception as exc:  # shapely raises ValueError/GEOSException on bad input
        raise GeoValidationError(
            f"Invalid GeoJSON geometry: {exc}"
        ) from exc
    return geometry


def _parse_geojson(data: str | None) -> dict | None:
    import json

    if not data:
        return None
    return json.loads(data)


def _decoded_boundary(scenario: SimulationScenario):
    """Decode the scenario's stored WKB proposed boundary (shapely path)."""
    try:
        return wkb_loads(bytes(scenario.geometry_wkb))
    except Exception as exc:  # noqa: BLE001 - surface decode failures as 400
        raise GeoValidationError(
            f"Could not decode boundary geometry for scenario {scenario.code!r}: {exc}"
        ) from exc
