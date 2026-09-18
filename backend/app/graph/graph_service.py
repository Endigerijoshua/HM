"""Deterministic responsibility graph semantics (P6).

The graph is an *explanatory view* of the P2 routing decision — it consumes
``ResponsibilityRoutingService.resolve`` and projects the result onto a chain:

    Location → Jurisdiction → Authority → Department → Service → Issue → Escalation

Nodes that the routing result does not carry (e.g. authority for an unresolved
responsibility, or jurisdiction for a gap) are simply omitted; the graph never
invents responsibility. Edges cover exactly the four role relations
``RESPONSIBLE_FOR | MANAGED_BY | HANDLED_BY | ESCALATES_TO`` and every node
has a stable id, a typespace and a human-readable label. Like the P2 result
itself, the graph is deterministic for the same (location, issue, date).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.issue_types import IssueType
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.routing.routing_service import ResponsibilityRoutingService
from app.schemas.graph import (
    AUTHORITY,
    DEPARTMENT,
    ESCALATES_TO,
    ESCALATION,
    HANDLED_BY,
    ISSUE,
    JURISDICTION,
    LOCATION,
    MANAGED_BY,
    RESPONSIBLE_FOR,
    SERVICE,
    GraphEdge,
    GraphNode,
    GraphResolveResponse,
)
from app.schemas.routing import RoutingResult


class ResponsibilityGraphService:
    """Build the responsibility chain from an existing P2 routing decision."""

    def __init__(
        self,
        db: Session,
        engine: TemporalJurisdictionEngine,
        provider: ShapelyGeometryProvider,
    ) -> None:
        self._db = db
        self._routing = ResponsibilityRoutingService(
            db=db, engine=engine, provider=provider
        )

    def resolve(
        self,
        *,
        latitude: float,
        longitude: float,
        issue_type: str,
        on_date: date,
    ) -> GraphResolveResponse:
        result = self._routing.resolve(
            longitude=longitude,
            latitude=latitude,
            issue_type=issue_type,
            on_date=on_date,
        )
        return self._build(result=result, issue_type=issue_type, on_date=on_date)

    # ------------------------------------------------------------------
    # graph projection
    # ------------------------------------------------------------------

    def _build(
        self,
        *,
        result: RoutingResult,
        issue_type: str,
        on_date: date,
    ) -> GraphResolveResponse:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        by_id: set[str] = set()

        def add_node(node: GraphNode) -> None:
            if node.id in by_id:
                return
            by_id.add(node.id)
            nodes.append(node)

        def add_edge(edge: GraphEdge) -> None:
            edges.append(edge)

        # Chain: Location → Jurisdiction → Authority → Department → Service → Issue.
        location_id = f"location:{result.longitude:.5f},{result.latitude:.5f}"
        jurisdiction_id: str | None = None
        authority_id: str | None = None
        department_id: str | None = None
        service_id: str | None = None
        issue_id = f"issue:{issue_type}"

        label = f"Location · {result.longitude:.4f}, {result.latitude:.4f}"
        add_node(GraphNode(id=location_id, type=LOCATION, label=label))

        if result.jurisdiction_code:
            jurisdiction_id = f"jurisdiction:{result.jurisdiction_code}"
            add_node(
                GraphNode(
                    id=jurisdiction_id,
                    type=JURISDICTION,
                    label=(
                        f"{result.jurisdiction_name or result.jurisdiction_code}"
                        f" ({result.jurisdiction_code})"
                    ),
                )
            )
            add_edge(
                GraphEdge(
                    id=f"{location_id}->{jurisdiction_id}",
                    source=location_id,
                    target=jurisdiction_id,
                    type=RESPONSIBLE_FOR,
                    label=(
                        f"{result.jurisdiction_name or result.jurisdiction_code}"
                        " is responsible for this location"
                    ),
                )
            )

        if result.authority is not None:
            authority_id = f"authority:{result.authority.code}"
            add_node(
                GraphNode(
                    id=authority_id,
                    type=AUTHORITY,
                    label=f"{result.authority.name} ({result.authority.code})",
                )
            )
        if result.department is not None:
            department_id = f"department:{result.department.code}"
            add_node(
                GraphNode(
                    id=department_id,
                    type=DEPARTMENT,
                    label=f"{result.department.name} ({result.department.code})",
                )
            )
        if result.service is not None:
            service_id = f"service:{result.service.code}"
            add_node(
                GraphNode(
                    id=service_id,
                    type=SERVICE,
                    label=f"{result.service.name} ({result.service.code})",
                )
            )

        issue_name = self._issue_name(issue_type) or issue_type
        add_node(
            GraphNode(
                id=issue_id,
                type=ISSUE,
                label=f"{issue_name} ({issue_type})",
            )
        )

        if jurisdiction_id and authority_id:
            add_edge(
                GraphEdge(
                    id=f"{jurisdiction_id}->{authority_id}",
                    source=jurisdiction_id,
                    target=authority_id,
                    type=MANAGED_BY,
                    label=(
                        f"{result.jurisdiction_name or result.jurisdiction_code}"
                        f" is administered by {result.authority.name}"
                    ),
                )
            )
        if authority_id and department_id:
            add_edge(
                GraphEdge(
                    id=f"{authority_id}->{department_id}",
                    source=authority_id,
                    target=department_id,
                    type=MANAGED_BY,
                    label=(
                        f"{result.department.name} is run by {result.authority.name}"
                    ),
                )
            )
        if department_id and service_id:
            add_edge(
                GraphEdge(
                    id=f"{department_id}->{service_id}",
                    source=department_id,
                    target=service_id,
                    type=HANDLED_BY,
                    label=(
                        f"{issue_name} is handled by {result.department.name}"
                        f" through the {result.service.name}"
                    ),
                )
            )
        if service_id:
            add_edge(
                GraphEdge(
                    id=f"{service_id}->{issue_id}",
                    source=service_id,
                    target=issue_id,
                    type=HANDLED_BY,
                    label=f"{result.service.name} covers {issue_name}",
                )
            )

        # When the chain cannot reach an actor (gap or tie), keep the graph
        # connected with an explicit explanatory edge instead of guessing.
        if jurisdiction_id and not authority_id:
            add_edge(
                GraphEdge(
                    id=f"{jurisdiction_id}->{issue_id}",
                    source=jurisdiction_id,
                    target=issue_id,
                    type=RESPONSIBLE_FOR,
                    label=(
                        f"{result.jurisdiction_name or result.jurisdiction_code}"
                        " holds the location, but no authority can be assigned"
                        f" ({result.status.value})"
                    ),
                )
            )
        elif not jurisdiction_id:
            add_edge(
                GraphEdge(
                    id=f"{location_id}->{issue_id}",
                    source=location_id,
                    target=issue_id,
                    type=RESPONSIBLE_FOR,
                    label="No jurisdiction contains the location — no authority"
                    f" can be assigned ({result.status.value})",
                )
            )

        # Escalation path (step nodes chain off the issue).
        previous_step: str | None = None
        for step in result.escalation_path:
            step_id = f"escalation:{step.step_number}"
            note = f" · {step.note}" if step.note else ""
            add_node(
                GraphNode(
                    id=step_id,
                    type=ESCALATION,
                    label=(
                        f"Escalation #{step.step_number} · "
                        f"{step.authority.name} · "
                        f"{step.department.name} / {step.service.name}{note}"
                    ),
                )
            )
            source = previous_step or issue_id
            add_edge(
                GraphEdge(
                    id=f"{source}->{step_id}",
                    source=source,
                    target=step_id,
                    type=ESCALATES_TO,
                    label=(
                        f"escalates to {step.authority.name} "
                        f"(#{step.step_number})"
                    ),
                )
            )
            previous_step = step_id

        return GraphResolveResponse(
            status=result.status.value,
            latitude=result.latitude,
            longitude=result.longitude,
            issue_type=issue_type,
            on_date=on_date,
            nodes=nodes,
            edges=edges,
            routing_id=result.audit_id,
            routing_rule_id=result.routing_rule_id,
            explanation=self._explain(result=result, issue_name=issue_name),
        )

    # ------------------------------------------------------------------
    # explanation
    # ------------------------------------------------------------------

    def _explain(self, *, result: RoutingResult, issue_name: str) -> str:
        status = result.status.value
        if result.authority and result.department and result.service:
            parts = [
                f"Location is inside {result.jurisdiction_name}"
                f" ({result.jurisdiction_code})"
                + (
                    f" on {result.effective_date.isoformat()} (By {result.version_code})"
                    if result.version_code
                    else ""
                )
                + ".",
                f"{result.jurisdiction_name} is administered by"
                f" {result.authority.name}.",
                (
                    f"The {issue_name} issue is handled by the"
                    f" {result.department.name} through the"
                    f" {result.service.name} service."
                ),
            ]
            if result.routing_rule_code:
                parts.append(
                    f"Matched by routing rule {result.routing_rule_code}."
                )
            return " ".join(parts)
        if result.jurisdiction_code and result.conflict_rule_codes:
            rules = ", ".join(sorted(result.conflict_rule_codes))
            return (
                f"Location is inside {result.jurisdiction_name}"
                f" ({result.jurisdiction_code}) on"
                f" {result.effective_date.isoformat()}, but the routing rules for"
                f" {issue_name} ({rules}) tie at equal priority — no single"
                " authority, department or service can be assigned"
                f" ({status})."
            )
        if not result.jurisdiction_code:
            return (
                f"On {result.effective_date.isoformat()} no jurisdiction"
                f" contains the location, so the {issue_name} issue cannot be"
                f" assigned to any authority ({status})."
            )
        return (
            f"Routing returned {status} for {issue_name} at"
            f" ({result.longitude:.4f}, {result.latitude:.4f})."
        )

    def _issue_name(self, code: str) -> str | None:
        if getattr(self, "_issue_names", None) is None:
            self._issue_names = dict(
                self._db.execute(select(IssueType.code, IssueType.name)).all()
            )
        return self._issue_names.get(code)