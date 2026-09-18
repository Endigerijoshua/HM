"""Deterministic responsibility conflict detection (P5).

The detector is deliberately small and explainable. It reuses the P2 routing
decision table and the P0/P1 temporal jurisdiction engine to answer the same
question twice per evaluation:

* expected responsibility — what the containing jurisdiction's owning
  authority/department/service *implies*; and
* routed responsibility — what the routing decision table *assigns*.

Any disagreement, or any gap where no responsibility can be established, is
recorded as a ``ResponsibilityConflict`` with a stable compound key
``(complaint_id, issue_type_code, on_date, conflict_type)`` so repeated runs
are deterministic and never duplicate rows.

Demo coverage (deterministic against the seeded dataset, date 2024-06-01):

* ``AUTHORITY_MISMATCH`` — C-1003 (geo A-MCC vs routed A-NHAI) and C-1008
  (geo A-MCC vs routed A-CESC).
* ``RESPONSIBILITY_GAP`` — C-1004 has no containing jurisdiction; the
  construction_waste probe at C-1002 ties between two equally-specific rules.
* ``DEPARTMENT_MISMATCH`` / ``SERVICE_MISMATCH`` — the C-1002 construction
  waste tie resolves to MCC-D-RI/SVC-ROAD (RULE-CW-DEV) versus
  MCC-D-HS/SVC-GARBAGE (RULE-CW-SAN).
* ``TEMPORAL_RULE_CONFLICT`` — power_outage at C-1008 has no responsible
  actor on 2024-03-15 (a gap between the 2020 and 2024 delimitation sets) but
  routes to A-CESC on 2024-06-01.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.ids import conflict_reference
from app.db.models.complaints import Complaint
from app.db.models.conflicts import ResponsibilityConflict
from app.db.models.issue_types import IssueType
from app.db.models.jurisdiction import Jurisdiction, JurisdictionVersion
from app.db.models.reference import Authority, Department, Service
from app.db.models.routing import RoutingRule
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.routing.routing_service import ResponsibilityRoutingService
from app.schemas.conflicts import (
    ConflictDetectResponse,
    ConflictListResponse,
    ConflictResponse,
)
from app.schemas.routing import ActorRef, RoutingResult, RoutingStatus

DETECTION_DATE = date(2024, 6, 1)
TEMPORAL_BEFORE_DATE = date(2024, 3, 15)
CONSTRUCTION_WASTE_ISSUE = "construction_waste"
POWER_OUTAGE_ISSUE = "power_outage"
CW_COMPLAINT_REF = "C-1002"
POWER_COMPLAINT_REF = "C-1008"

AUTHORITY_MISMATCH = "AUTHORITY_MISMATCH"
DEPARTMENT_MISMATCH = "DEPARTMENT_MISMATCH"
SERVICE_MISMATCH = "SERVICE_MISMATCH"
TEMPORAL_RULE_CONFLICT = "TEMPORAL_RULE_CONFLICT"
RESPONSIBILITY_GAP = "RESPONSIBILITY_GAP"

LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"
OPEN = "OPEN"


class ResponsibilityConflictService:
    """Detect, store and surface deterministic responsibility conflicts."""

    def __init__(
        self,
        db: Session,
        engine: TemporalJurisdictionEngine,
        provider: ShapelyGeometryProvider,
    ) -> None:
        self._db = db
        self._engine = engine
        self._provider = provider
        self._routing = ResponsibilityRoutingService(
            db=db, engine=engine, provider=provider
        )

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------

    def list_conflicts(self, status: str | None = None) -> ConflictListResponse:
        query = select(ResponsibilityConflict).order_by(
            ResponsibilityConflict.id.desc()
        )
        if status:
            query = query.where(ResponsibilityConflict.status == status.upper())
        rows = list(self._db.scalars(query))
        return ConflictListResponse(
            count=len(rows), conflicts=[self._payload(row) for row in rows]
        )

    def get_conflict(self, conflict_id: str) -> ConflictResponse:
        row = self._db.scalar(
            select(ResponsibilityConflict).where(
                ResponsibilityConflict.code == conflict_id
            )
        )
        if row is None:
            raise NotFoundError(f"Conflict {conflict_id!r} does not exist")
        return self._payload(row)

    # ------------------------------------------------------------------
    # detection
    # ------------------------------------------------------------------

    def detect(self) -> ConflictDetectResponse:
        """Run the deterministic detector and persist new conflicts.

        Re-running the detector is safe: an identical open conflict
        (same complaint, issue, date and type) is never duplicated.
        """
        existing = self._existing_keys()
        added: list[ResponsibilityConflict] = []
        evaluated = 0

        complaints = list(
            self._db.scalars(
                select(Complaint)
                .where(Complaint.status == "OPEN")
                .order_by(Complaint.id)
            )
        )
        for complaint in complaints:
            self._evaluate_open_complaint(
                complaint, existing=existing, added=added
            )
            evaluated += 1

        evaluated += self._probe_construction_waste(
            existing=existing, added=added
        )
        evaluated += self._probe_temporal_outage(existing=existing, added=added)

        self._db.commit()

        return ConflictDetectResponse(
            detection_date=DETECTION_DATE,
            evaluated=evaluated,
            created=len(added),
            count=len(added),
            conflicts=[self._payload(row) for row in added],
        )

    def _evaluate_open_complaint(
        self,
        complaint: Complaint,
        *,
        existing: set,
        added: list[ResponsibilityConflict],
    ) -> None:
        result = self._resolve(
            complaint=complaint, issue_type=complaint.issue_type_code
        )
        on_date = DETECTION_DATE
        if result.status == RoutingStatus.NO_JURISDICTION:
            self._add(
                complaint=complaint,
                issue_type=complaint.issue_type_code,
                on_date=on_date,
                conflict_type=RESPONSIBILITY_GAP,
                severity=HIGH,
                explanation=(
                    f"{complaint.public_ref} at ({complaint.lng:.4f}, "
                    f"{complaint.lat:.4f}) for {complaint.issue_type_code} on "
                    f"{on_date} lies outside every jurisdiction; the routing "
                    "decision table cannot assign any authority — unresolved "
                    "responsibility gap."
                ),
                existing=existing,
                added=added,
            )
        elif result.status == RoutingStatus.RESPONSIBILITY_UNRESOLVED:
            self._add(
                complaint=complaint,
                issue_type=complaint.issue_type_code,
                on_date=on_date,
                conflict_type=RESPONSIBILITY_GAP,
                severity=HIGH,
                explanation=(
                    f"{complaint.public_ref} at ({complaint.lng:.4f}, "
                    f"{complaint.lat:.4f}) for {complaint.issue_type_code} on "
                    f"{on_date} cannot be settled: candidate rules "
                    f"{sorted(result.conflict_rule_codes)} tie at every "
                    "equally-specific level — unresolved responsibility gap."
                ),
                existing=existing,
                added=added,
            )
        elif result.status == RoutingStatus.RESOLVED:
            jurisdiction = self._provider.jurisdiction_at(
                complaint.lng, complaint.lat, on_date
            )
            if (
                jurisdiction is not None
                and jurisdiction.authority is not None
                and result.authority is not None
                and jurisdiction.authority.id != result.authority.id
            ):
                self._add(
                    complaint=complaint,
                    issue_type=complaint.issue_type_code,
                    on_date=on_date,
                    conflict_type=AUTHORITY_MISMATCH,
                    severity=HIGH,
                    jurisdiction_code=jurisdiction.code,
                    expected_authority=jurisdiction.authority,
                    routed_authority=result.authority,
                    routed_department=result.department,
                    routed_service=result.service,
                    explanation=(
                        f"{complaint.public_ref} at ({complaint.lng:.4f}, "
                        f"{complaint.lat:.4f}) lies inside {jurisdiction.name} "
                        f"({jurisdiction.code}), whose owning authority is "
                        f"{jurisdiction.authority.name}, but the routing rule "
                        f"assigns {complaint.issue_type_code} to "
                        f"{result.authority.name} "
                        f"({result.department.name} / {result.service.name}) — "
                        "jurisdiction vs routing-authority mismatch."
                    ),
                    existing=existing,
                    added=added,
                )

    def _probe_construction_waste(
        self, *, existing: set, added: list[ResponsibilityConflict]
    ) -> int:
        """Tie between two equally-specific construction-waste rules (P5)."""
        complaint = self._db.scalar(
            select(Complaint).where(
                Complaint.public_ref == CW_COMPLAINT_REF
            )
        )
        if complaint is None:
            return 0
        result = self._resolve(
            complaint=complaint, issue_type=CONSTRUCTION_WASTE_ISSUE
        )
        if (
            result.status != RoutingStatus.RESPONSIBILITY_UNRESOLVED
            or not result.conflict_rule_codes
        ):
            return 0
        rules = list(
            self._db.scalars(
                select(RoutingRule)
                .where(RoutingRule.code.in_(result.conflict_rule_codes))
                .order_by(RoutingRule.id)
            )
        )
        if len(rules) < 2:
            return 0
        first, second = rules[0], rules[1]
        jurisdiction = self._provider.jurisdiction_at(
            complaint.lng, complaint.lat, DETECTION_DATE
        )
        jurisdiction_code = jurisdiction.code if jurisdiction else None
        jurisdiction_name = jurisdiction.name if jurisdiction else "no jurisdiction"

        self._add(
            complaint=complaint,
            issue_type=CONSTRUCTION_WASTE_ISSUE,
            on_date=DETECTION_DATE,
            conflict_type=RESPONSIBILITY_GAP,
            severity=HIGH,
            jurisdiction_code=jurisdiction_code,
            expected_authority=jurisdiction.authority if jurisdiction else None,
            routed_authority=jurisdiction.authority if jurisdiction else None,
            expected_department=first.department,
            expected_service=first.service,
            routed_department=second.department,
            routed_service=second.service,
            explanation=(
                f"{complaint.public_ref} at ({complaint.lng:.4f}, "
                f"{complaint.lat:.4f}) raising {CONSTRUCTION_WASTE_ISSUE} "
                f"ties between {first.code} "
                f"(→ {first.department.name} / {first.service.name}) and "
                f"{second.code} (→ {second.department.name} / "
                f"{second.service.name}); the decision table cannot settle a "
                f"single responsible department/service inside "
                f"{jurisdiction_name} — unresolved responsibility gap."
            ),
            existing=existing,
            added=added,
        )

        self._add(
            complaint=complaint,
            issue_type=CONSTRUCTION_WASTE_ISSUE,
            on_date=DETECTION_DATE,
            conflict_type=DEPARTMENT_MISMATCH,
            severity=MEDIUM,
            jurisdiction_code=jurisdiction_code,
            expected_authority=jurisdiction.authority if jurisdiction else None,
            routed_authority=jurisdiction.authority if jurisdiction else None,
            expected_department=first.department,
            routed_department=second.department,
            explanation=(
                f"The {jurisdiction_code}-scoped {CONSTRUCTION_WASTE_ISSUE} "
                f"rules route to different departments: "
                f"{first.department.name} ({first.department.code}) via "
                f"{first.code} vs {second.department.name} "
                f"({second.department.code}) via {second.code} — expected "
                "department vs routed department mismatch."
            ),
            existing=existing,
            added=added,
        )

        self._add(
            complaint=complaint,
            issue_type=CONSTRUCTION_WASTE_ISSUE,
            on_date=DETECTION_DATE,
            conflict_type=SERVICE_MISMATCH,
            severity=MEDIUM,
            jurisdiction_code=jurisdiction_code,
            expected_authority=jurisdiction.authority if jurisdiction else None,
            routed_authority=jurisdiction.authority if jurisdiction else None,
            expected_service=first.service,
            routed_service=second.service,
            explanation=(
                f"The {jurisdiction_code}-scoped {CONSTRUCTION_WASTE_ISSUE} "
                f"rules route to different services: {first.service.name} "
                f"({first.service.code}) via {first.code} vs "
                f"{second.service.name} ({second.service.code}) via "
                f"{second.code} — expected service vs routed service mismatch."
            ),
            existing=existing,
            added=added,
        )
        return 1

    def _probe_temporal_outage(
        self, *, existing: set, added: list[ResponsibilityConflict]
    ) -> int:
        """Same location+issue resolving differently across date (P5)."""
        complaint = self._db.scalar(
            select(Complaint).where(
                Complaint.public_ref == POWER_COMPLAINT_REF
            )
        )
        if complaint is None:
            return 0
        before = self._resolve(
            complaint=complaint, issue_type=POWER_OUTAGE_ISSUE,
            on_date=TEMPORAL_BEFORE_DATE,
        )
        after = self._resolve(
            complaint=complaint, issue_type=POWER_OUTAGE_ISSUE,
            on_date=DETECTION_DATE,
        )
        if not (
            before.authority is None
            and after.status == RoutingStatus.RESOLVED
            and after.authority is not None
        ):
            return 0
        jurisdiction = self._provider.jurisdiction_at(
            complaint.lng, complaint.lat, DETECTION_DATE
        )
        window = self._version_gap_description()
        self._add(
            complaint=complaint,
            issue_type=POWER_OUTAGE_ISSUE,
            on_date=TEMPORAL_BEFORE_DATE,
            conflict_type=TEMPORAL_RULE_CONFLICT,
            severity=MEDIUM,
            jurisdiction_code=jurisdiction.code if jurisdiction else None,
            expected_authority=jurisdiction.authority if jurisdiction else None,
            routed_authority=after.authority,
            routed_department=after.department,
            routed_service=after.service,
            explanation=(
                f"{complaint.public_ref} at ({complaint.lng:.4f}, "
                f"{complaint.lat:.4f}) raising {POWER_OUTAGE_ISSUE} is routed "
                f"to {after.authority.name} "
                f"({after.department.name} / {after.service.name}) on "
                f"{DETECTION_DATE}, but no responsible actor existed on "
                f"{TEMPORAL_BEFORE_DATE} ({window}) — responsibility changed "
                "over time at the same location, a temporal rule conflict."
            ),
            existing=existing,
            added=added,
        )
        return 1

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _resolve(
        self,
        *,
        complaint: Complaint,
        issue_type: str,
        on_date: date = DETECTION_DATE,
    ) -> RoutingResult:
        return self._routing.resolve(
            longitude=complaint.lng,
            latitude=complaint.lat,
            issue_type=issue_type,
            on_date=on_date,
        )

    def _existing_keys(self) -> set:
        rows = self._db.execute(
            select(
                ResponsibilityConflict.complaint_id,
                ResponsibilityConflict.issue_type_code,
                ResponsibilityConflict.on_date,
                ResponsibilityConflict.conflict_type,
            )
        ).all()
        return {
            (
                row[0],
                row[1],
                row[2].isoformat() if row[2] else None,
                row[3],
            )
            for row in rows
        }

    def _add(
        self,
        *,
        complaint: Complaint,
        issue_type: str,
        on_date: date,
        conflict_type: str,
        severity: str,
        explanation: str,
        existing: set,
        added: list[ResponsibilityConflict],
        jurisdiction_code: str | None = None,
        expected_authority: Authority | None = None,
        routed_authority: Authority | None = None,
        expected_department: Department | None = None,
        routed_department: Department | None = None,
        expected_service: Service | None = None,
        routed_service: Service | None = None,
    ) -> ResponsibilityConflict | None:
        key = (
            complaint.id,
            issue_type,
            on_date.isoformat(),
            conflict_type,
        )
        if key in existing:
            return None
        existing.add(key)
        row = ResponsibilityConflict(
            code=conflict_reference(),
            status=OPEN,
            conflict_type=conflict_type,
            severity=severity,
            lat=complaint.lat,
            lng=complaint.lng,
            complaint_id=complaint.id,
            issue_type_code=issue_type,
            on_date=on_date,
            jurisdiction_code=jurisdiction_code,
            geo_authority_id=expected_authority.id if expected_authority else None,
            service_authority_id=routed_authority.id if routed_authority else None,
            expected_department_id=expected_department.id if expected_department else None,
            expected_service_id=expected_service.id if expected_service else None,
            routed_department_id=routed_department.id if routed_department else None,
            routed_service_id=routed_service.id if routed_service else None,
            description=explanation,
        )
        self._db.add(row)
        added.append(row)
        return row

    def _version_gap_description(self) -> str:
        versions = list(
            self._db.scalars(
                select(JurisdictionVersion).order_by(
                    JurisdictionVersion.version_no
                )
            )
        )
        if len(versions) >= 2:
            earlier, later = versions[0], versions[1]
            return (
                f"between {earlier.code} (valid until {earlier.effective_to}) "
                f"and {later.code} (valid from {later.effective_from})"
            )
        return "the interval between jurisdiction versions"

    def _payload(self, row: ResponsibilityConflict) -> ConflictResponse:
        complaint_ref = row.complaint.public_ref if row.complaint else None
        return ConflictResponse(
            conflict_id=row.code,
            latitude=row.lat,
            longitude=row.lng,
            complaint_ref=complaint_ref,
            issue_type=row.issue_type_code,
            issue_type_name=self._issue_name(row.issue_type_code),
            on_date=row.on_date,
            jurisdiction_code=row.jurisdiction_code,
            jurisdiction_name=self._jurisdiction_name(row.jurisdiction_code),
            expected_authority=_actor(row.geo_authority),
            routed_authority=_actor(row.service_authority),
            expected_department=_actor(row.expected_department),
            routed_department=_actor(row.routed_department),
            expected_service=_actor(row.expected_service),
            routed_service=_actor(row.routed_service),
            conflict_type=row.conflict_type,
            severity=row.severity,
            explanation=row.description,
            status=row.status,
            created_at=row.created_at.isoformat() if row.created_at else None,
        )

    def _issue_name(self, code: str | None) -> str | None:
        if not code:
            return None
        if getattr(self, "_issue_names", None) is None:
            self._issue_names = dict(
                self._db.execute(select(IssueType.code, IssueType.name)).all()
            )
        return self._issue_names.get(code)

    def _jurisdiction_name(self, code: str | None) -> str | None:
        if not code:
            return None
        if getattr(self, "_jurisdiction_names", None) is None:
            rows = self._db.execute(
                select(
                    Jurisdiction.code,
                    Jurisdiction.name,
                    Jurisdiction.effective_from,
                ).order_by(Jurisdiction.effective_from)
            ).all()
            names: dict[str, str] = {}
            for row_code, row_name, _from in rows:
                names[row_code] = row_name
            self._jurisdiction_names = names
        return self._jurisdiction_names.get(code)


def _actor(row) -> ActorRef | None:
    if row is None:
        return None
    return ActorRef(id=row.id, code=row.code, name=row.name)