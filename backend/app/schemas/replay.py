"""Schemas for the historical jurisdiction replay API (P7).

The replay endpoint resolves one ``(location, issue, date)`` triple across a
date range, day-by-day, reusing the P1 temporal jurisdiction engine and the P2
routing service. Consecutive days with identical state are merged into a single
period so the response surfaces exactly the timeline of
jurisdiction/responsibility changes that a judge can walk through.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.routing import ActorRef, RoutingStatus


class ReplayPeriod(BaseModel):
    """One maximal run of days (closed-open ``[effective_from, effective_to)``)
    where the resolved jurisdiction/responsibility state did not change."""

    effective_from: date
    effective_to: date
    status: RoutingStatus
    # True when this period's state differs from the immediately preceding one
    # (always False for the first period).
    boundary_change: bool

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
    routing_rule_code: str | None = None
    routing_rule_id: int | None = None
    conflict_rule_codes: list[str] = Field(default_factory=list)

    # Outcome detail.
    explanation: str | None = None
    reason: str | None = None

    # Compact readable chain, e.g. "W-05 → A-MCC → MCC-D-HP".
    chain: str | None = None


class ReplayPointResponse(BaseModel):
    """Chronological responsibility summary for a point over a date range."""

    status: str = "REPLAY_OK"
    latitude: float
    longitude: float
    issue_type: str
    start_date: date
    end_date: date
    # [start_date, end_date) day count, only for transparency.
    day_count: int
    period_count: int
    # Number of times the jurisdiction code changed between consecutive periods.
    jurisdiction_change_count: int
    periods: list[ReplayPeriod]