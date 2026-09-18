"""P2 civic responsibility routing engine tests.

Covers: deterministic resolution, scope precedence, tie handling, temporal
replay across the 2020→2024 delimitation, the heritage overlay (covering
jurisdictions), deliberate ownership conflicts, the issue-type registry, the
rules catalogue, 422 validation and the append-only audit trail.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.db.models import AuditLog, Jurisdiction
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.gis.temporal_engine import TemporalJurisdictionEngine
from app.routing.routing_service import ResponsibilityRoutingService
from app.schemas.routing import RoutingStatus
from app.seed.seed_runner import _flip_coords


def _v2_jurisdiction(db, code: str) -> Jurisdiction:
    return (
        db.query(Jurisdiction)
        .filter(Jurisdiction.code == code, Jurisdiction.effective_from == date(2024, 4, 1))
        .one()
    )


def _point_in(db, provider, code: str) -> tuple[float, float]:
    """Return a (lng, lat) guaranteed to sit strictly inside the V2 jurisdiction."""
    geometry = provider.geometry_for(_v2_jurisdiction(db, code))
    point = geometry.representative_point()
    return point.x, point.y


def _build_routing(db, provider) -> ResponsibilityRoutingService:
    return ResponsibilityRoutingService(db, TemporalJurisdictionEngine(provider), provider)


@pytest.fixture(autouse=True)
def _commit_writes(db):
    """The session-scoped db fixture holds flushed-but-uncommitted audit rows
    after direct-service tests. Commit after every test so no open write
    transaction blocks the API client's own session on SQLite."""
    yield
    db.commit()


def test_resolve_pothole_routes_to_mcc_roads(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "W-05")

    result = routing.resolve(longitude=lng, latitude=lat, issue_type="pothole", on_date=date(2024, 6, 1))

    assert result.status is RoutingStatus.RESOLVED
    assert result.routing_rule_code == "RULE-POTHOLE"
    assert result.matched_scope == "AUTHORITY_WIDE"
    assert result.authority.code == "A-MCC"
    assert result.department.code == "MCC-D-RI"
    assert result.service.code == "SVC-ROAD"
    assert result.sla_days == 5
    assert result.ward_code == "W-05"
    assert result.version_code == "DELIM-2024"
    assert result.explanation is not None

    escalation = [step.step_number for step in result.escalation_path]
    assert escalation == [1, 2]
    assert result.escalation_path[0].authority.code == "A-MCC"
    assert result.escalation_path[1].authority.code == "A-PWD"


def test_resolve_heritage_issue_uses_covering_jurisdiction(db) -> None:
    """A point inside HER-01 is also inside a ward; the heritage-scoped rule
    must win via covering-jurisdiction matching even though the primary lookup
    returns the ward."""
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "HER-01")

    result = routing.resolve(
        longitude=lng, latitude=lat, issue_type="heritage_maintenance",
        on_date=date(2024, 6, 1),
    )

    assert result.status is RoutingStatus.RESOLVED
    assert result.routing_rule_code == "RULE-HERITAGE-01"
    assert result.matched_scope == "JURISDICTION"
    assert result.department.code == "MCC-D-HP"
    assert result.service.code == "SVC-HERITAGE"
    assert "Heritage Precinct" in result.explanation
    assert len(result.escalation_path) == 1


def test_resolve_construction_waste_conflict(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "W-05")

    result = routing.resolve(
        longitude=lng, latitude=lat, issue_type="construction_waste",
        on_date=date(2024, 6, 1),
    )

    assert result.status is RoutingStatus.RESPONSIBILITY_UNRESOLVED
    assert result.conflict_rule_codes == ["RULE-CW-DEV", "RULE-CW-SAN"]
    assert result.authority is None
    assert result.department is None
    assert result.service is None
    assert result.matched_scope == "JURISDICTION"
    assert result.reason is not None


def test_resolve_unrouted_issue_is_unresolved(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "W-05")

    result = routing.resolve(
        longitude=lng, latitude=lat, issue_type="public_property_damage",
        on_date=date(2024, 6, 1),
    )

    assert result.status is RoutingStatus.RESPONSIBILITY_UNRESOLVED
    assert "No active routing rule" in result.reason
    assert result.conflict_rule_codes == []


def test_resolve_flip_point_temporal_garbage(db) -> None:
    """Same coordinate, same issue: the expired and current rules swap at the
    2024 delimitation while both keep the same responsible department."""
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lon, lat = _flip_coords()

    before = routing.resolve(longitude=lon, latitude=lat, issue_type="garbage", on_date=date(2023, 6, 1))
    after = routing.resolve(longitude=lon, latitude=lat, issue_type="garbage", on_date=date(2024, 6, 1))

    assert before.status is RoutingStatus.RESOLVED
    assert after.status is RoutingStatus.RESOLVED
    assert before.routing_rule_code == "RULE-GARBAGE-HIST"
    assert after.routing_rule_code == "RULE-GARBAGE"
    assert before.version_code == "DELIM-2020"
    assert after.version_code == "DELIM-2024"
    assert before.ward_code != after.ward_code
    assert before.department.code == after.department.code == "MCC-D-HS"
    assert before.service.code == after.service.code == "SVC-GARBAGE"


def test_resolve_nh_rule_overrides_geography(db) -> None:
    """A rule-based attribution (NHAI) correctly wins even inside an MCC ward."""
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "W-05")

    result = routing.resolve(longitude=lng, latitude=lat, issue_type="nh_repair", on_date=date(2024, 6, 1))

    assert result.status is RoutingStatus.RESOLVED
    assert result.authority.code == "A-NHAI"
    assert result.service.code == "SVC-NH"


def test_resolve_unknown_issue(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)

    result = routing.resolve(longitude=76.6, latitude=12.3, issue_type="ufo_sighting", on_date=date(2024, 6, 1))

    assert result.status is RoutingStatus.INVALID_ISSUE
    assert result.audit_id is not None


def test_resolve_date_before_data_window(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)

    result = routing.resolve(longitude=76.6, latitude=12.3, issue_type="garbage", on_date=date(2019, 6, 1))

    assert result.status is RoutingStatus.INVALID_DATE
    assert "2020" in result.reason


def test_resolve_date_in_delimitation_gap(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)

    result = routing.resolve(longitude=76.6, latitude=12.3, issue_type="garbage", on_date=date(2024, 1, 5))

    assert result.status is RoutingStatus.NO_JURISDICTION


def test_resolve_out_of_range_coordinates(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)

    result = routing.resolve(longitude=181.0, latitude=12.0, issue_type="garbage", on_date=date(2024, 6, 1))

    assert result.status is RoutingStatus.INVALID_LOCATION


def test_resolution_is_deterministic_and_audited(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "W-05")

    first = routing.resolve(longitude=lng, latitude=lat, issue_type="drainage", on_date=date(2024, 6, 1))
    second = routing.resolve(longitude=lng, latitude=lat, issue_type="drainage", on_date=date(2024, 6, 1))

    assert first.routing_rule_code == second.routing_rule_code == "RULE-DRAINAGE"
    assert first.explanation == second.explanation
    assert first.audit_id != second.audit_id

    log = db.get(AuditLog, first.audit_id)
    assert log is not None
    assert log.action == "routing.resolve"
    assert log.entity_type == "routing_result"
    assert log.entity_id == "RULE-DRAINAGE"
    assert log.route_reference.startswith("RT-")
    assert log.after_data["status"] == "RESOLVED"
    assert log.after_data["rule_code"] == "RULE-DRAINAGE"
    assert log.after_data["issue_type"] == "drainage"
    assert log.after_data["effective_date"] == "2024-06-01"
    assert log.after_data["jurisdiction_version_code"] == "DELIM-2024"


def test_conflicts_are_audited_as_unresolved(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "W-05")

    result = routing.resolve(
        longitude=lng, latitude=lat, issue_type="construction_waste",
        on_date=date(2024, 6, 1),
    )

    log = db.get(AuditLog, result.audit_id)
    assert log.after_data["status"] == "RESPONSIBILITY_UNRESOLVED"
    assert log.after_data["conflict_rule_codes"] == ["RULE-CW-DEV", "RULE-CW-SAN"]


def test_all_taxonomy_codes_route(db) -> None:
    provider = ShapelyGeometryProvider(db)
    routing = _build_routing(db, provider)
    lng, lat = _point_in(db, provider, "W-05")

    codes = [
        "garbage", "garbage_collection", "overflowing_bin", "illegal_dumping",
        "street_sweeping", "public_toilet", "pothole", "road_repair",
        "road_damage", "drain_cleaning", "drainage", "water_supply",
        "sewage", "sewage_overflow", "streetlight", "street_light",
        "layout_approval", "sh_repair", "nh_repair", "power_outage",
    ]
    for code in codes:
        result = routing.resolve(longitude=lng, latitude=lat, issue_type=code, on_date=date(2024, 6, 1))
        assert result.status is RoutingStatus.RESOLVED, code
        assert result.authority is not None and result.service is not None, code


# ----------------------------------------------------------------------
# API level
# ----------------------------------------------------------------------


def _w05_lat_lng(db) -> tuple[float, float]:
    provider = ShapelyGeometryProvider(db)
    lng, lat = _point_in(db, provider, "W-05")
    return lat, lng


def test_api_resolve_known_issue(client) -> None:
    resp = client.post(
        "/api/v1/routing/resolve",
        json={"latitude": 12.3125, "longitude": 76.6375, "issue_type": "garbage", "date": "2024-06-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "RESOLVED"
    assert body["routing_rule_code"] == "RULE-GARBAGE"
    assert body["authority"]["code"] == "A-MCC"
    assert body["audit_id"] is not None


def test_api_resolve_conflict_returns_200_with_status(client, db) -> None:
    lat, lng = _w05_lat_lng(db)
    resp = client.post(
        "/api/v1/routing/resolve",
        json={"latitude": lat, "longitude": lng, "issue_type": "construction_waste", "date": "2024-06-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "RESPONSIBILITY_UNRESOLVED"
    assert sorted(body["conflict_rule_codes"]) == ["RULE-CW-DEV", "RULE-CW-SAN"]


def test_api_resolve_invalid_coordinates_returns_422(client) -> None:
    resp = client.post(
        "/api/v1/routing/resolve",
        json={"latitude": 95.0, "longitude": 12.3, "issue_type": "garbage", "date": "2024-06-01"},
    )
    assert resp.status_code == 422


def test_api_issue_types_endpoint(client) -> None:
    resp = client.get("/api/v1/routing/issue-types")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 23
    codes = {item["code"] for item in body["issue_types"]}
    assert {"garbage", "pothole", "construction_waste", "public_property_damage"} <= codes


def test_api_rules_endpoint_filters(client) -> None:
    resp = client.get(
        "/api/v1/routing/rules",
        params={"issue_type": "construction_waste", "active_on": "2024-06-01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert {rule["code"] for rule in body["rules"]} == {"RULE-CW-DEV", "RULE-CW-SAN"}


def test_api_rules_historical_filter(client) -> None:
    resp = client.get("/api/v1/routing/rules", params={"active_on": "2023-06-01"})
    assert resp.status_code == 200
    body = resp.json()
    codes = {rule["code"] for rule in body["rules"]}
    assert "RULE-GARBAGE-HIST" in codes
    assert "RULE-GARBAGE" not in codes