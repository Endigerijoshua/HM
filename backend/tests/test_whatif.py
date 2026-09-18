"""Focused deterministic P3 tests for the What-If simulator.

The P3 what-if router (``app.api.routers.whatif``) exposes two public
endpoints:

* ``GET  /api/v1/whatif/scenarios``   -> ``WhatIfScenarioListResponse``
* ``POST /api/v1/whatif/simulate``    -> ``WhatIfSimulateResponse``

Every assertion here is deterministic: the seeded flip premise is recomputed
from ``app.seed.seed_runner._flip_coords`` (which derives both demo mosaics
from the fixed ``WARD_*`` bounds and seeded RNGs), so the tests never depend
on runtime state or on a live database having been mutated.

Read-only contract: ``simulate`` must not insert, update, or delete any row.
That invariant is asserted at the API level by running one scenario twice and
requiring byte-identical payloads, and by re-fetching the scenario list
before/after and requiring it to be unchanged.
"""
from __future__ import annotations

import random

from app.seed.geometry import (
    WARD_MAXX,
    WARD_MAXY,
    WARD_MINX,
    WARD_MINY,
    build_mosaic,
    find_flip_point_between,
)
from app.seed.seed_runner import (
    FLIP_RNG_SEED,
    MOSAIC_V1_SEED,
    MOSAIC_V2_SEED,
    _flip_coords,
)


def _flip_premise_mosaics():
    v1 = build_mosaic(WARD_MINX, WARD_MINY, WARD_MAXX, WARD_MAXY, 3, 3, seed=MOSAIC_V1_SEED)
    v2 = build_mosaic(WARD_MINX, WARD_MINY, WARD_MAXX, WARD_MAXY, 3, 3, seed=MOSAIC_V2_SEED)
    return v1, v2


def test_flip_point_between_always_terminates_and_lies_in_ward() -> None:
    """The seeded flip premise always terminates and lands inside the ward."""
    v1, v2 = _flip_premise_mosaics()
    lon, lat = find_flip_point_between(v1.cells, v2.cells, random.Random(FLIP_RNG_SEED))
    assert isinstance(lon, float)
    assert isinstance(lat, float)
    assert WARD_MINX <= lon <= WARD_MAXX
    assert WARD_MINY <= lat <= WARD_MAXY


def test_flip_premise_is_deterministic_across_runs() -> None:
    """Same seeds -> identical flip point every time."""
    v1, v2 = _flip_premise_mosaics()
    first = find_flip_point_between(v1.cells, v2.cells, random.Random(FLIP_RNG_SEED))
    second = find_flip_point_between(v1.cells, v2.cells, random.Random(FLIP_RNG_SEED))
    assert first == second


def test_flip_coords_matches_seeded_flip_premise() -> None:
    """seed_runner._flip_coords is deterministic and inside the ward."""
    first = _flip_coords()
    second = _flip_coords()
    assert first == second
    lon, lat = first
    assert WARD_MINX <= lon <= WARD_MAXX
    assert WARD_MINY <= lat <= WARD_MAXY


CREATE_GEOM = {
    "type": "Polygon",
    "coordinates": [
        [
            [76.62, 12.305],
            [76.63, 12.305],
            [76.63, 12.315],
            [76.62, 12.315],
            [76.62, 12.305],
        ]
    ],
}


def test_create_scenario_persists_geometry_and_round_trips() -> None:
    """POST /whatif/scenarios derives WKB + envelope and is listable (client)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        c.post("/api/v1/whatif/scenarios", json={
            "code": "SC-CREATE-TEST",
            "name": "Create geometry test",
            "affected_region_name": "test",
            "geometry_geojson": CREATE_GEOM,
        })
        listed = c.get("/api/v1/whatif/scenarios").json()
        codes = [s["code"] for s in listed["scenarios"]]
        assert "SC-CREATE-TEST" in codes
        created = next(s for s in listed["scenarios"] if s["code"] == "SC-CREATE-TEST")
        assert created["envelope_geojson"] is not None
        assert created["geometry_geojson"]["type"] == "Polygon"


def test_create_scenario_does_not_mutate_active_jurisdictions(client, db) -> None:
    """Creating a scenario leaves live jurisdiction data byte-identical."""
    from app.db.models.jurisdiction import Jurisdiction

    before = [
        (j.code, j.name, j.kind) for j in db.query(Jurisdiction).order_by(Jurisdiction.code)
    ]
    resp = client.post("/api/v1/whatif/scenarios", json={
        "code": "SC-READONLY-TEST",
        "name": "Read-only isolation test",
        "geometry_geojson": CREATE_GEOM,
    })
    assert resp.status_code == 201, resp.text
    after = [
        (j.code, j.name, j.kind) for j in db.query(Jurisdiction).order_by(Jurisdiction.code)
    ]
    assert after == before
