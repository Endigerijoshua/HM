"""Civic responsibility routing API (P2).

Endpoints
---------
* ``GET  /routing/issue-types``  - catalogue of recognised civic issues
* ``GET  /routing/rules``        - routing-rule decision table (filterable)
* ``POST /routing/resolve``      - route an issue to the responsible civic actor

Resolve always answers with HTTP 200; success/failure is carried in the
``status`` field so citizens see any outcome clearly (see ``RoutingResult``).
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_routing_service
from app.db.models.issue_types import IssueType
from app.db.models.routing import RoutingRule
from app.routing.routing_service import ResponsibilityRoutingService
from app.schemas.routing import (
    IssueTypeListResponse,
    IssueTypeSummary,
    RouteResolveRequest,
    RoutingResult,
    RoutingRuleListResponse,
    RoutingRuleSummary,
)

router = APIRouter(prefix="/routing", tags=["routing"])


@router.get(
    "/issue-types",
    response_model=IssueTypeListResponse,
    summary="Catalogue of recognised civic issues",
)
def list_issue_types(
    db: Session = Depends(get_db),
) -> IssueTypeListResponse:
    rows = (
        db.query(IssueType)
        .order_by(IssueType.category, IssueType.code)
        .all()
    )
    items = [
        IssueTypeSummary(
            code=row.code,
            name=row.name,
            category=row.category,
            description=row.description,
            is_active=row.is_active,
        )
        for row in rows
    ]
    return IssueTypeListResponse(count=len(items), issue_types=items)


@router.get(
    "/rules",
    response_model=RoutingRuleListResponse,
    summary="List routing rules, optionally filtered",
)
def list_rules(
    issue_type: str | None = Query(None, description="Only rules for this issue code"),
    active_on: date | None = Query(None, description="Only rules in force on this date"),
    db: Session = Depends(get_db),
) -> RoutingRuleListResponse:
    stmt = select(RoutingRule)
    if issue_type is not None:
        stmt = stmt.where(RoutingRule.issue_type_code == issue_type)
    if active_on is not None:
        stmt = stmt.where(
            RoutingRule.effective_from <= active_on,
            or_(RoutingRule.effective_to.is_(None), active_on < RoutingRule.effective_to),
        )
    rows = list(db.scalars(stmt.order_by(RoutingRule.code)))
    items = [_rule_summary(row, on_date=active_on) for row in rows]
    return RoutingRuleListResponse(
        count=len(items),
        active_on=active_on,
        issue_type=issue_type,
        rules=items,
    )


@router.post(
    "/resolve",
    response_model=RoutingResult,
    summary="Route an issue to the responsible civic actor",
    description=(
        "Deterministically attributes civic responsibility for an issue at a "
        "point on a date. Returns 200 with a status in all business outcomes."
    ),
)
def resolve_route(
    request: RouteResolveRequest,
    service: ResponsibilityRoutingService = Depends(get_routing_service),
    db: Session = Depends(get_db),
) -> RoutingResult:
    result = service.resolve(
        longitude=request.longitude,
        latitude=request.latitude,
        issue_type=request.issue_type,
        on_date=request.on_date,
    )
    db.commit()
    return result


def _rule_summary(rule: RoutingRule, *, on_date: date | None) -> RoutingRuleSummary:
    return RoutingRuleSummary(
        id=rule.id,
        code=rule.code,
        issue_type_code=rule.issue_type_code,
        scope=rule.scope,
        priority=rule.priority,
        rationale=rule.rationale,
        effective_from=rule.effective_from,
        effective_to=rule.effective_to,
        authority_code=rule.authority.code,
        authority_name=rule.authority.name,
        department_code=rule.department.code,
        department_name=rule.department.name,
        service_code=rule.service.code,
        service_name=rule.service.name,
        jurisdiction_code=rule.jurisdiction.code if rule.jurisdiction else None,
        active_on=on_date,
    )