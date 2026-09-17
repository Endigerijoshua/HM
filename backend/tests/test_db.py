"""Database schema initialisation tests."""
from __future__ import annotations

from sqlalchemy import inspect

from app.db.session import engine, init_db

EXPECTED_TABLES = {
    "authorities",
    "departments",
    "services",
    "jurisdictions",
    "jurisdiction_versions",
    "jurisdiction_changes",
    "wards",
    "roads",
    "areas",
    "routing_rules",
    "complaints",
    "complaint_events",
    "responsibility_conflicts",
    "migration_plans",
    "migration_items",
    "simulation_scenarios",
    "audit_logs",
}


def test_all_expected_tables_created() -> None:
    init_db()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    assert EXPECTED_TABLES <= table_names


def test_jurisdictions_temporal_structure() -> None:
    init_db()
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("jurisdictions")}
    required = {
        "id",
        "code",
        "kind",
        "authority_id",
        "jurisdiction_version_id",
        "geometry_geojson",
        "geometry_wkb",
        "envelope_geojson",
        "effective_from",
        "effective_to",
        "superseded_by_id",
    }
    assert required <= columns


def test_audit_logs_store_json_payloads() -> None:
    init_db()
    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("audit_logs")}
    assert {"before_data", "after_data", "action", "entity_type", "created_at"} <= columns


def test_migration_tables_linked() -> None:
    init_db()
    inspector = inspect(engine)
    for table in ("migration_plans", "migration_items"):
        names = {c["name"] for c in inspector.get_columns(table)}
        assert "complaint_id" in names or "scenario_id" in names