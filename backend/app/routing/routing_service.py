"""Civic responsibility routing service (P2).

Combines the temporal jurisdiction engine (P1) with the routing-rule decision
table to answer one question deterministically:

    Who is responsible for ``issue_type`` at ``(longitude, latitude)`` on ``date``?

Resolution rules
----------------
1. Candidates are routing rules active on the date (closed-open
   ``[effective_from, effective_to)``) whose ``issue_type_code`` matches and
   whose geographic matching is enabled.
2. More specific scope wins: a ``JURISDICTION``-scoped rule whose jurisdiction
   covers the point beats any ``AUTHORITY_WIDE`` rule.
3. Within the winning scope, the lowest ``priority`` wins; ties are broken
   deterministically by ``id``. A tie that would route to *different*
   authority/department/service targets is surfaced as
   ``RESPONSIBILITY_UNRESOLVED`` (an ownership conflict) rather than guessed.
4. Valid issues with no matching rule are surfaced as unresolved too, so gaps
   in the decision table are visible instead of silently producing a route.
5. Every resolution — success or not — is written to the append-only audit log
   with the full input triple and the outcome, so decisions are replayable.

All outcomes return HTTP 200 from the API with a ``status`` field; the service
never raises for business outcomes.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.ids import route_reference
from app.db.models.audit import AuditLog
from app.db.models.escalation import EscalationStep
from app.db.models.issue_types import IssueType
from app.db.models.reference import Authority, Department, Service
from app.db.models.routing import RoutingRule
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.schemas.gis import JurisdictionLookupResult, LookupStatus
from app.schemas.routing import (
    ActorRef,
    EscalationStepRef,
    RoutingResult,
    RoutingStatus,
)

DATA_MIN_DATE = date(2020, 1, 1)


class ResponsibilityRoutingService:
    """Resolves the responsible civic actor for a (location, issue, date) triple."""

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
    # public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        *,
        longitude: float,
        latitude: float,
        issue_type: str,
        on_date: date,
    ) -> RoutingResult:
        """Route an issue; always returns a ``RoutingResult`` with a status."""
        if on_date < DATA_MIN_DATE:
            return self._record_result(
                longitude=longitude,
                latitude=latitude,
                issue_type=issue_type,
                on_date=on_date,
                status=RoutingStatus.INVALID_DATE,
                reason=(
                    "No jurisdictional or routing data exists before "
                    f"{DATA_MIN_DATE.isoformat()}."
                ),
            )

        if not self._recognised_issue(issue_type):
            return self._record_result(
                longitude=longitude,
                latitude=latitude,
                issue_type=issue_type,
                on_date=on_date,
                status=RoutingStatus.INVALID_ISSUE,
                reason=f"Unknown issue type {issue_type!r}. See GET /routing/issue-types.",
            )

        lookup = self._engine.resolve_jurisdiction_at_point(longitude, latitude, on_date)
        mapped = self._map_lookup_status(lookup)
        if mapped is not None:
            return self._record_result(
                longitude=longitude,
                latitude=latitude,
                issue_type=issue_type,
                on_date=on_date,
                status=mapped,
                reason=lookup.message,
                lookup=lookup,
            )

        covering = self._provider.jurisdictions_containing(longitude, latitude, on_date)
        covering_ids = {j.id for j in covering}

        candidates = self._active_rules(issue_type, on_date)
        scoped = [
            r for r in candidates if r.scope == "JURISDICTION" and r.jurisdiction_id in covering_ids
        ]
        wide = [r for r in candidates if r.scope == "AUTHORITY_WIDE"]
        pool = scoped if scoped else wide
        pool_scope = pool[0].scope if pool else None

        if not pool:
            return self._record_result(
                longitude=longitude,
                latitude=latitude,
                issue_type=issue_type,
                on_date=on_date,
                status=RoutingStatus.RESPONSIBILITY_UNRESOLVED,
                reason=(
                    f"No active routing rule defines responsibility for "
                    f"{issue_type!r} on {on_date.isoformat()}."
                ),
                lookup=lookup,
            )

        min_priority = min(r.priority for r in pool)
        tied = sorted(
            (r for r in pool if r.priority == min_priority),
            key=lambda r: (r.priority, r.id),
        )
        targets = {(r.authority_id, r.department_id, r.service_id) for r in tied}

        if len(targets) > 1:
            codes = [r.code for r in tied]
            return self._record_result(
                longitude=longitude,
                latitude=latitude,
                issue_type=issue_type,
                on_date=on_date,
                status=RoutingStatus.RESPONSIBILITY_UNRESOLVED,
                reason=(
                    f"{len(tied)} equally-specific rules for {issue_type!r} apply at this "
                    f"point on {on_date.isoformat()} but disagree on the responsible "
                    f"department/service ({', '.join(codes)}); responsibility cannot be "
                    "determined deterministically."
                ),
                lookup=lookup,
                matched_scope=pool_scope,
                conflict_rule_codes=codes,
            )

        rule = tied[0]
        return self._resolved_result(longitude, latitude, issue_type, on_date, lookup, rule)

    # ------------------------------------------------------------------
    # internals: rule / actor lookups
    # ------------------------------------------------------------------

    def _recognised_issue(self, issue_type: str) -> bool:
        stmt = select(IssueType.code).where(IssueType.code == issue_type)
        return self._db.scalar(stmt) is not None

    def _active_rules(self, issue_type: str, on_date: date) -> list[RoutingRule]:
        stmt = (
            select(RoutingRule)
            .where(
                RoutingRule.issue_type_code == issue_type,
                RoutingRule.match_geography.is_(True),
                RoutingRule.effective_from <= on_date,
                or_(RoutingRule.effective_to.is_(None), on_date < RoutingRule.effective_to),
            )
            .order_by(RoutingRule.id)
        )
        return list(self._db.scalars(stmt))

    def _escalation_path(self, rule_id: int) -> list[EscalationStepRef]:
        rows = (
            self._db.query(EscalationStep)
            .filter(EscalationStep.routing_rule_id == rule_id)
            .order_by(EscalationStep.step_number, EscalationStep.id)
            .all()
        )
        return [
            EscalationStepRef(
                step_number=row.step_number,
                authority=self._actor(row.authority),
                department=self._actor(row.department),
                service=self._actor(row.service),
                note=row.note,
            )
            for row in rows
        ]

    @staticmethod
    def _actor(entity: Authority | Department | Service) -> ActorRef:
        return ActorRef(id=entity.id, code=entity.code, name=entity.name)

    # ------------------------------------------------------------------
    # internals: result construction
    # ------------------------------------------------------------------

    @staticmethod
    def _map_lookup_status(lookup: JurisdictionLookupResult) -> RoutingStatus | None:
        if lookup.status is LookupStatus.INVALID_COORDINATES:
            return RoutingStatus.INVALID_LOCATION
        if lookup.status is LookupStatus.NO_JURISDICTION:
            return RoutingStatus.NO_JURISDICTION
        if lookup.status is LookupStatus.TEMPORAL_CONFLICT:
            return RoutingStatus.TEMPORAL_CONFLICT
        if lookup.status is LookupStatus.INVALID_GEOMETRY:
            return RoutingStatus.RESPONSIBILITY_UNRESOLVED
        return None

    def _resolved_result(
        self,
        longitude: float,
        latitude: float,
        issue_type: str,
        on_date: date,
        lookup: JurisdictionLookupResult,
        rule: RoutingRule,
    ) -> RoutingResult:
        authority = self._db.get(Authority, rule.authority_id)
        department = self._db.get(Department, rule.department_id)
        service = self._db.get(Service, rule.service_id)
        explanation = self._explain(lookup, on_date, rule, authority, department, service)

        return self._record_result(
            longitude=longitude,
            latitude=latitude,
            issue_type=issue_type,
            on_date=on_date,
            status=RoutingStatus.RESOLVED,
            lookup=lookup,
            matched_scope=rule.scope,
            conflict_rule_codes=[],
            rule=rule,
            authority=authority,
            department=department,
            service=service,
            explanation=explanation,
        )

    def _explain(
        self,
        lookup: JurisdictionLookupResult,
        on_date: date,
        rule: RoutingRule,
        authority: Authority,
        department: Department,
        service: Service,
    ) -> str:
        parts: list[str] = []
        if lookup.jurisdiction is not None:
            place = f"{lookup.jurisdiction.code} ({lookup.jurisdiction.name})"
            if lookup.ward is not None:
                place += f", ward {lookup.ward.ward_code} {lookup.ward.name}"
            if lookup.version is not None:
                place += f", under {lookup.version.code}"
            parts.append(
                f"The point falls inside {place}, in force on {on_date.isoformat()}."
            )
        if rule.scope == "JURISDICTION" and rule.jurisdiction is not None:
            parts.append(
                f"The {rule.code} rule is scoped to jurisdiction {rule.jurisdiction.name} "
                f"({rule.jurisdiction.code}), which covers this point."
            )
        else:
            parts.append(f"The {rule.code} rule applies authority-wide.")
        parts.append(
            f"Responsibility therefore sits with {authority.name} ({authority.code}), "
            f"{department.name} ({department.code}) and {service.name} ({service.code})."
        )
        parts.append(f"Rule rationale: {rule.rationale}")
        return " ".join(parts)

    def _record_result(
        self,
        *,
        longitude: float,
        latitude: float,
        issue_type: str,
        on_date: date,
        status: RoutingStatus,
        reason: str | None = None,
        lookup: JurisdictionLookupResult | None = None,
        matched_scope: str | None = None,
        conflict_rule_codes: list[str] | None = None,
        rule: RoutingRule | None = None,
        authority: Authority | None = None,
        department: Department | None = None,
        service: Service | None = None,
        explanation: str | None = None,
    ) -> RoutingResult:
        may_select = lookup is not None
        result = RoutingResult(
            status=status,
            latitude=latitude,
            longitude=longitude,
            issue_type=issue_type,
            effective_date=on_date,
            jurisdiction_code=getattr(lookup.jurisdiction, "code", None) if may_select else None,
            jurisdiction_name=getattr(lookup.jurisdiction, "name", None) if may_select else None,
            jurisdiction_kind=getattr(lookup.jurisdiction, "kind", None) if may_select else None,
            version_code=getattr(lookup.version, "code", None) if may_select else None,
            version_status=getattr(lookup.version, "status", None) if may_select else None,
            ward_code=getattr(lookup.ward, "ward_code", None) if may_select else None,
            ward_name=getattr(lookup.ward, "name", None) if may_select else None,
            matched_scope=matched_scope,
            authority=self._actor(authority) if authority else None,
            department=self._actor(department) if department else None,
            service=self._actor(service) if service else None,
            sla_days=service.sla_days if service else None,
            routing_rule_code=rule.code if rule else None,
            routing_rule_id=rule.id if rule else None,
            escalation_path=self._escalation_path(rule.id) if rule else [],
            conflict_rule_codes=conflict_rule_codes or [],
            explanation=explanation,
            reason=reason,
        )
        audit_id = self._audit(
            longitude=longitude,
            latitude=latitude,
            issue_type=issue_type,
            on_date=on_date,
            status=status,
            reason=reason,
            lookup=lookup,
            matched_scope=matched_scope,
            conflict_rule_codes=conflict_rule_codes,
            rule=rule,
            authority=authority,
            department=department,
            service=service,
        )
        result.audit_id = audit_id
        return result

    def _audit(
        self,
        *,
        longitude: float,
        latitude: float,
        issue_type: str,
        on_date: date,
        status: RoutingStatus,
        reason: str | None,
        lookup: JurisdictionLookupResult | None,
        matched_scope: str | None,
        conflict_rule_codes: list[str] | None,
        rule: RoutingRule | None,
        authority: Authority | None,
        department: Department | None,
        service: Service | None,
    ) -> int:
        after = {
            "longitude": longitude,
            "latitude": latitude,
            "issue_type": issue_type,
            "effective_date": on_date.isoformat(),
            "status": status.value,
            "jurisdiction_code": lookup.jurisdiction.code if lookup and lookup.jurisdiction else None,
            "jurisdiction_version_code": lookup.version.code if lookup and lookup.version else None,
            "ward_code": lookup.ward.ward_code if lookup and lookup.ward else None,
            "matched_scope": matched_scope,
            "rule_code": rule.code if rule else None,
            "authority_code": authority.code if authority else None,
            "department_code": department.code if department else None,
            "service_code": service.code if service else None,
            "conflict_rule_codes": conflict_rule_codes or [],
            "reason": reason,
        }
        log = AuditLog(
            actor="api",
            actor_role="citizen",
            action="routing.resolve",
            entity_type="routing_result",
            entity_id=rule.code if rule else None,
            before_data=None,
            after_data=after,
            ip=None,
            route_reference=route_reference(),
        )
        self._db.add(log)
        self._db.flush()
        return log.id