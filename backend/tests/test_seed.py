"""Seed data integrity and temporal semantics tests."""
from __future__ import annotations

import json
from datetime import date

from shapely.geometry import shape

from app.core.ids import route_reference
from app.db.models import (
    Area,
    AuditLog,
    Authority,
    Complaint,
    ComplaintEvent,
    Department,
    EscalationStep,
    IssueType,
    Jurisdiction,
    JurisdictionChange,
    JurisdictionVersion,
    MigrationPlan,
    ResponsibilityConflict,
    Road,
    RoutingRule,
    Service,
    SimulationScenario,
    Ward,
)
from app.gis.shapely_provider import ShapelyGeometryProvider
from app.seed.seed_runner import _flip_coords, seed_all


def test_seed_counts(db) -> None:
    assert db.query(Authority).count() == 5
    assert db.query(Department).count() == 10
    assert db.query(Service).count() == 13
    assert db.query(IssueType).count() == 23
    assert db.query(EscalationStep).count() == 3
    assert db.query(JurisdictionVersion).count() == 3
    assert db.query(Jurisdiction).count() == 21  # 9 wards + corridor (V1); 9 wards + corridor + heritage (V2)
    assert db.query(JurisdictionChange).count() >= 3
    assert db.query(Ward).count() == 9
    assert db.query(Area).count() == 3
    assert db.query(Road).count() == 4
    assert db.query(RoutingRule).count() == 25
    assert db.query(Complaint).count() == 9
    assert db.query(ComplaintEvent).count() == 9
    assert db.query(ResponsibilityConflict).count() == 1
    assert db.query(SimulationScenario).count() == 1
    assert db.query(MigrationPlan).count() == 1


def test_seed_is_idempotent(db) -> None:
    stats = seed_all(db)
    db.commit()
    assert stats.jurisdictions == 21
    assert db.query(Complaint).count() == 9


def test_jurisdiction_version_statuses(db) -> None:
    v1 = db.query(JurisdictionVersion).filter_by(code="DELIM-2020").one()
    assert v1.status == "SUPERSEDED"
    assert v1.effective_to == date(2023, 12, 31)

    v2 = db.query(JurisdictionVersion).filter_by(code="DELIM-2024").one()
    assert v2.status == "CURRENT"
    assert v2.effective_to is None

    v3 = db.query(JurisdictionVersion).filter_by(code="REZONE-2026-DRAFT").one()
    assert v3.status == "PROPOSED"


def test_historical_data_never_overwritten(db) -> None:
    rows = (
        db.query(Jurisdiction)
        .filter(Jurisdiction.code == "W-01")
        .order_by(Jurisdiction.effective_from)
        .all()
    )
    assert len(rows) == 2
    v1_row, v2_row = rows
    assert v1_row.effective_to == date(2023, 12, 31)
    assert v2_row.effective_from == date(2024, 4, 1)
    assert v2_row.effective_to is None
    assert v1_row.superseded_by_id == v2_row.id
    assert v1_row.geometry_wkb != v2_row.geometry_wkb


def test_historical_replay_flip_point(db) -> None:
    """The same coordinate must resolve to a different ward per date."""
    lon, lat = _flip_coords()
    provider = ShapelyGeometryProvider(db)
    before = provider.jurisdiction_at(lon, lat, date(2023, 6, 1))
    after = provider.jurisdiction_at(lon, lat, date(2024, 6, 1))
    assert before is not None and after is not None
    assert before.code != after.code


def test_flip_complaint_uses_flip_point(db) -> None:
    complaint = db.query(Complaint).filter(Complaint.public_ref == "C-1001").one()
    provider = ShapelyGeometryProvider(db)
    before = provider.jurisdiction_at(complaint.lng, complaint.lat, date(2023, 6, 1))
    after = provider.jurisdiction_at(complaint.lng, complaint.lat, date(2024, 6, 1))
    assert before and after and before.code != after.code


def test_expired_rule_still_archived(db) -> None:
    rule = db.query(RoutingRule).filter_by(code="RULE-GARBAGE-PRE2024").one()
    assert rule.effective_to == date(2023, 12, 31)
    active = db.query(RoutingRule).filter_by(code="RULE-GARBAGE-01").one()
    assert active.effective_to is None


def test_scenario_geometry_valid_and_isolated(db) -> None:
    scenario = db.query(SimulationScenario).filter_by(code="SC-V3-REZONE").one()
    assert scenario.status == "DRAFT"
    geometry = shape(json.loads(scenario.geometry_geojson))
    assert geometry.is_valid
    assert geometry.geom_type == "Polygon"
    # The scenario must NOT have introduced rows into the live jurisdictions table.
    heritage_live = (
        db.query(Jurisdiction)
        .filter(Jurisdiction.code == "W-01", Jurisdiction.effective_from == date(2026, 7, 1))
        .all()
    )
    assert heritage_live == []


def test_audit_logs_seeded(db) -> None:
    assert db.query(AuditLog).filter(AuditLog.action == "seed.loaded").count() >= 1


def test_reference_id_shape() -> None:
    reference = route_reference()
    assert reference.startswith("RT-")
    assert len(reference) >= 20