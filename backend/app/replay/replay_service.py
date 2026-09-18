"""P7 historical jurisdiction replay.

Resolves the same ``(location, issue, date)`` triple independently for every
day in a date range by calling the already-verified P2 routing service, then
merges consecutive identical outcomes into stable periods. This adds no routing
logic of its own; the strict closed-open ``[from, to)`` semantics of the
temporal engines are preserved because each sample is an independent resolution.

The endpoint never commits: replay is strictly read-only so it does not write an
audit row per replayed day.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.core.errors import DateRangeError
from app.routing.routing_service import ResponsibilityRoutingService
from app.schemas.replay import ReplayPeriod, ReplayPointResponse
from app.schemas.routing import RoutingResult, RoutingStatus

# Guard against pathological ranges; the contract documents a closed-open
# window the caller chooses.
MAX_WINDOW_DAYS = 4000


def replay_point(
    *,
    routing_service: ResponsibilityRoutingService,
    longitude: float,
    latitude: float,
    issue_type: str,
    start: date,
    end: date,
) -> ReplayPointResponse:
    """Resolve the same coordinate independently for every date in [start, end).

    One period is emitted whenever the day-to-day (jurisdiction, version, ward,
    actor, rule) outcome changes, so boundary transitions are explicit and a
    judge can replay the exact day a boundary version or routing rule took
    effect. Business outcomes (NO_JURISDICTION, RESPONSIBILITY_UNRESOLVED,
    INVALID_ISSUE, ...) are returned as periods, never raised.
    """
    if end < start:
        raise DateRangeError(
            f"Date range must be closed-open with start <= end, got "
            f"start={start.isoformat()} end={end.isoformat()}."
        )
    day_count = (end - start).days
    if day_count > MAX_WINDOW_DAYS:
        raise DateRangeError(
            f"Date range {start.isoformat()}..{end.isoformat()} spans "
            f"{day_count} days; the replay window is limited to "
            f"{MAX_WINDOW_DAYS} days."
        )

    records: list[tuple[date, RoutingResult]] = []
    prev_state: tuple[object, ...] | None = None
    day = start
    while day < end:
        result = routing_service.resolve(
            longitude=longitude,
            latitude=latitude,
            issue_type=issue_type,
            on_date=day,
        )
        state = _state_key(result)
        if state != prev_state:
            records.append((day, result))
            prev_state = state
        day += timedelta(days=1)

    periods: list[ReplayPeriod] = []
    for index, (from_date, result) in enumerate(records):
        to_date = records[index + 1][0] if index + 1 < len(records) else end
        periods.append(
            _period(
                from_date=from_date,
                to_date=to_date,
                result=result,
                boundary_change=index > 0,
            )
        )

    jurisdictions = [p.jurisdiction_code for p in periods]
    jurisdiction_change_count = sum(
        1
        for i in range(1, len(jurisdictions))
        if jurisdictions[i] != jurisdictions[i - 1]
    )

    return ReplayPointResponse(
        latitude=latitude,
        longitude=longitude,
        issue_type=issue_type,
        start_date=start,
        end_date=end,
        day_count=day_count,
        period_count=len(periods),
        jurisdiction_change_count=jurisdiction_change_count,
        periods=periods,
    )


def _state_key(result: RoutingResult) -> tuple[object, ...]:
    """Identity of a routing outcome: any change ends the current period."""
    return (
        result.status,
        result.jurisdiction_code,
        result.version_code,
        result.jurisdiction_kind,
        result.authority.code if result.authority else None,
        result.department.code if result.department else None,
        result.service.code if result.service else None,
        result.routing_rule_code,
        tuple(result.conflict_rule_codes or []),
    )


def _period(
    *,
    from_date: date,
    to_date: date,
    result: RoutingResult,
    boundary_change: bool,
) -> ReplayPeriod:
    return ReplayPeriod(
        effective_from=from_date,
        effective_to=to_date,
        status=result.status,
        boundary_change=boundary_change,
        jurisdiction_code=result.jurisdiction_code,
        jurisdiction_name=result.jurisdiction_name,
        jurisdiction_kind=result.jurisdiction_kind,
        version_code=result.version_code,
        version_status=result.version_status,
        ward_code=result.ward_code,
        ward_name=result.ward_name,
        matched_scope=result.matched_scope,
        authority=result.authority if result.authority else None,
        department=result.department if result.department else None,
        service=result.service if result.service else None,
        routing_rule_code=result.routing_rule_code,
        routing_rule_id=result.routing_rule_id,
        conflict_rule_codes=list(result.conflict_rule_codes or []),
        explanation=result.explanation,
        reason=result.reason,
        chain=_chain(result),
    )


def _chain(result: RoutingResult) -> str | None:
    """Compact readable chain, e.g. "W-05 → A-MCC → MCC-D-HP"."""
    jurisdiction = result.jurisdiction_code or "(no jurisdiction)"
    if result.status is RoutingStatus.NO_JURISDICTION:
        return "(no jurisdiction)"
    if result.status is RoutingStatus.INVALID_LOCATION:
        return "(invalid location)"
    if result.status is RoutingStatus.INVALID_ISSUE:
        return f"{jurisdiction} → (unknown issue)"
    if result.status is RoutingStatus.INVALID_DATE:
        return f"{jurisdiction} → (out of data window)"
    if result.status is RoutingStatus.TEMPORAL_CONFLICT:
        return f"{jurisdiction} → (temporal conflict)"
    if result.department is not None:
        return f"{jurisdiction} → {result.authority.code if result.authority else '?'} → {result.department.code}"
    if result.authority is not None:
        return f"{jurisdiction} → {result.authority.code}"
    return f"{jurisdiction} → (unresolved)"