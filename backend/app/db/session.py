"""Database engine, session factory and initialisation helpers (SQLite in P0)."""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    # Allow the same connection to be shared across FastAPI's sync threads.
    _connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def init_db() -> None:
    """Bring the database in line with the ORM models.

    Stored tables are reconciled with any columns added to models after the
    SQLite file was first created (schema upgrade), then all modelled tables
    that do not exist yet are created.
    """
    from app.db import models as models  # noqa: F401  (registration side-effect)
    from app.db.schema_upgrade import upgrade_schema

    upgrade_schema(engine)
    models.Base.metadata.create_all(bind=engine)


def db_healthcheck(db: Session) -> bool:
    """Return True when the database responds to a trivial query."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - health check must not raise
        return False