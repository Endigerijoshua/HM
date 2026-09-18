"""Lightweight idempotent schema upgrade for SQLite.

``Base.metadata.create_all`` creates *missing* tables but never alters an
existing one. When a pre-existing SQLite database file was created by an
earlier schema than the current ORM models, the model and the stored table
drift apart and startup fails with errors such as::

    sqlite3.OperationalError: no such column: responsibility_conflicts.severity

Concretely, ``responsibility_conflicts`` predates the P5 columns and the
existing ``temporal_civic.db`` therefore lacks ``severity`` plus the
at-level department/service columns.

This module reconciles models with storage by adding any model columns that
are missing from an existing table using SQLite's data-preserving
``ALTER TABLE ... ADD COLUMN``. It never drops or renames columns or tables
and never rewrites rows, so existing seeded demo data survives the upgrade.
The reconcile is model-driven: any future model column addition is picked up
automatically on startup without new migration code.

Boundary: SQLite can only ``ADD COLUMN`` columns that are nullable or carry a
server default. A non-null column without a default would require a full
table rebuild, which is out of scope for this prototype; such columns are
skipped with a warning.
"""
from __future__ import annotations

import logging

from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine.interfaces import Dialect

from app.db.base import Base

logger = logging.getLogger("app.db.schema_upgrade")


def _column_definition(table_name: str, column, dialect: Dialect) -> str:
    """Render the ``ALTER TABLE ... ADD COLUMN`` clause for a model column."""
    preparer = dialect.identifier_preparer
    name = preparer.quote(column.name)
    column_type = column.type.compile(dialect=dialect)
    return f"{name} {column_type}"


def upgrade_schema(engine: Engine) -> list[str]:
    """Add any ORM model columns missing from existing SQLite tables.

    Runs inside a single transaction and is safe to call repeatedly.
    Returns the list of ``<table>.<column>`` additions performed.
    """
    import app.db.models  # noqa: F401  (register all models on Base.metadata)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    dialect = engine.dialect

    plan: list[tuple[str, object]] = []
    for table_name, table in sorted(Base.metadata.tables.items()):
        if table_name not in existing_tables:
            continue  # created from scratch by create_all
        actual_columns = {col["name"] for col in inspector.get_columns(table_name)}
        for name, column in table.columns.items():
            if name in actual_columns:
                continue
            if column.nullable is False and column.server_default is None:
                logger.warning(
                    "Skipping %s.%s: adding a NOT NULL column without a server "
                    "default requires a SQLite table rebuild",
                    table_name,
                    name,
                )
                continue
            plan.append((table_name, column))

    if not plan:
        return []

    with engine.begin() as conn:
        for table_name, column in plan:
            ddl = _column_definition(table_name, column, dialect)
            statement = f"ALTER TABLE {table_name} ADD COLUMN {ddl}"
            conn.execute(text(statement))
            logger.info("Schema upgrade: %s", statement)

        # create_all does not manage the indexes of pre-existing tables, so
        # recreate indexes for columns that were just added with index=True.
        for table_name, column in plan:
            if not column.index:
                continue
            index_name = f"ix_{table_name}_{column.name}"
            index_ddl = (
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON {table_name} ({column.name})"
            )
            conn.execute(text(index_ddl))

    return [f"{table}.{column.name}" for table, column in plan]