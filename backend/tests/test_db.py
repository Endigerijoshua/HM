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


def test_upgrade_schema_reconciles_stale_responsibility_conflicts() -> None:
    """A pre-existing table missing model columns is upgraded in place."""
    from sqlalchemy import create_engine
    from sqlalchemy import text as sql_text

    from app.db.schema_upgrade import upgrade_schema

    stale_engine = create_engine("sqlite://")
    with stale_engine.begin() as conn:
        conn.execute(
            sql_text(
                "CREATE TABLE responsibility_conflicts ("
                " id INTEGER PRIMARY KEY,"
                " code VARCHAR(20) NOT NULL,"
                " status VARCHAR(20) NOT NULL,"
                " conflict_type VARCHAR(30) NOT NULL,"
                " lat FLOAT NOT NULL,"
                " lng FLOAT NOT NULL,"
                " complaint_id INTEGER,"
                " geo_authority_id INTEGER,"
                " service_authority_id INTEGER,"
                " description TEXT NOT NULL,"
                " resolution_note TEXT,"
                " resolved_at DATETIME,"
                " created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,"
                " updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL)"
            )
        )
        conn.execute(
            sql_text(
                "INSERT INTO responsibility_conflicts"
                " (code, status, conflict_type, lat, lng, description)"
                " VALUES ('CF-LEGACY', 'OPEN', 'GEO_VS_SERVICE',"
                " 12.31, 76.63, 'legacy row')"
            )
        )

    added = upgrade_schema(stale_engine)

    stale_inspector = inspect(stale_engine)
    columns = {
        c["name"] for c in stale_inspector.get_columns("responsibility_conflicts")
    }
    for expected in (
        "severity",
        "issue_type_code",
        "on_date",
        "jurisdiction_code",
        "expected_department_id",
        "expected_service_id",
        "routed_department_id",
        "routed_service_id",
    ):
        assert expected in columns

    # Existing rows survive the upgrade.
    with stale_engine.connect() as conn:
        row = conn.execute(
            sql_text(
                "SELECT code, severity FROM responsibility_conflicts"
                " WHERE code = 'CF-LEGACY'"
            )
        ).one()
    assert row.code == "CF-LEGACY"
    assert row.severity is None

    # The upgrade is idempotent: a second pass applies no further changes.
    assert upgrade_schema(stale_engine) == []
    assert {f"responsibility_conflicts.{c}" for c in ("severity", "on_date")} <= set(added)