"""Pytest fixtures for the Temporal Civic Jurisdiction Digital Twin backend."""
from __future__ import annotations

import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="tcivic_test_")
os.environ["TCIVIC_DATABASE_URL"] = "sqlite:///" + _TMP_DIR.replace(os.sep, "/") + "/test.db"
os.environ["TCIVIC_SEED_ON_STARTUP"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.seed_runner import seed_all  # noqa: E402

# Ensure tables exist even before the app lifespan has run once.
init_db()


@pytest.fixture(scope="session")
def db():
    """Session-scoped SQLite session with seeded demo data."""
    session = SessionLocal()
    seed_all(session)
    session.commit()
    yield session
    session.close()


@pytest.fixture(scope="session")
def provider(db):
    from app.gis.shapely_provider import ShapelyGeometryProvider

    yield ShapelyGeometryProvider(db)


@pytest.fixture()
def client():
    """TestClient; the app lifespan seeds the (already seeded) database."""
    with TestClient(app) as test_client:
        yield test_client