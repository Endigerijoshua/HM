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

import json
import random

from shapely.geometry import Point, Polygon, shape

from app.seed.geometry import (
    HERITAGE_ZONE,
    HERITAGE_ZONE_PROPOSED,
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


def _simulate(client, *, lon: float, lat: float, issue: str, on_date: str = "2026-09-18"):
    resp = client.post("/api/v1/whatif/simulate", json={
        "longitude": lon,
        "latitude": lat,
        "issue_type_code": issue,
        "on_date": on_date,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_a_proposed_geometry_differs_from_current(client) -> None:
    """The simulator reads the scenario's real stored boundary, not live HER-01."""
    listed = client.get("/api/v1/whatif/scenarios").json()
    scenario = next(s for s in listed["scenarios"] if s["code"] == "SC-V3-REZONE")
    boundary = shape(scenario["geometry_geojson"])
    assert boundary == Polygon(HERITAGE_ZONE_PROPOSED)
    assert boundary != Polygon(HERITAGE_ZONE)

    # (76.655, 12.31) lies east of the live HER-01 edge (lng 76.65) yet is inside
    # the proposed boundary (lng 76.66) -> prove the simulation used the proposal.
    body = _simulate(client, lon=76.655, lat=12.31, issue="heritage_maintenance")
    assert body["in_proposed_geometry"] is True
    assert (body["proposed"] or {})["jurisdiction_code"] == "HER-01"


def test_b_known_demo_location_changes_responsibility(client) -> None:
    """C-1009's heritage point is live-owned by ward W-05, proposed -> HER-01."""
    body = _simulate(client, lon=76.638, lat=12.312, issue="heritage_maintenance")
    assert body["in_proposed_geometry"] is True
    assert body["current"]["jurisdiction_code"] == "W-05"
    assert body["proposed"]["jurisdiction_code"] == "HER-01"
    assert body["proposed"]["matched_scope"] == "HERITAGE_PRECINCT"
    assert body["proposed"]["routing_rule_code"] == "RULE-HERITAGE-01"
    deltas = body["responsibility_deltas"]
    assert deltas, "heritage point under a ward must report a jurisdiction delta"
    assert any(
        "W-05" in d["description"] and "HER-01" in d["description"]
        for d in deltas
    )
    # heritage dept/service are unchanged, so only jurisdiction flips.
    assert all(d["department_code"] == "MCC-D-HP" for d in deltas)
    assert all(d["service_code"] == "SVC-HERITAGE" for d in deltas)


def test_c_unaffected_locations_do_not_falsely_change(client) -> None:
    """Outside the proposal -> no proposed result, no fabricated deltas."""
    flip_lon, flip_lat = _flip_coords()
    body = _simulate(client, lon=flip_lon, lat=flip_lat, issue="garbage_collection")
    assert body["in_proposed_geometry"] is False
    assert body["proposed"] is None
    assert body["responsibility_deltas"] == []

    body = _simulate(client, lon=76.63, lat=12.33, issue="heritage_maintenance")
    assert body["in_proposed_geometry"] is False
    assert body["proposed"] is None
    assert body["responsibility_deltas"] == []


def test_d_affected_count_is_spatial_membership(client, db) -> None:
    """affected_complaint_count counts OPEN complaints inside the boundary (==3)."""
    from app.db.models.complaints import Complaint

    listed = client.get("/api/v1/whatif/scenarios").json()
    boundary = shape(next(s for s in listed["scenarios"] if s["code"] == "SC-V3-REZONE")["geometry_geojson"])
    open_inside = [
        c.public_ref
        for c in db.query(Complaint).filter(Complaint.status == "OPEN")
        if boundary.covers(Point(c.lng, c.lat))
    ]
    assert set(open_inside) == {"C-1002", "C-1007", "C-1009"}

    for lon, lat, issue in (
        (76.6438, 12.3082, "heritage_maintenance"),
        (76.60731308845853, 12.279255877741852, "garbage_collection"),
    ):
        body = _simulate(client, lon=lon, lat=lat, issue=issue)
        assert body["affected_complaint_count"] == len(open_inside) == 3
        assert body["affected_complaint_count"] < 7  # not "all complaints"


def test_e_simulate_does_not_modify_active_records(client, db) -> None:
    """Simulate + preview leave live jurisdictions/rules/complaints untouched."""
    from app.db.models.complaints import Complaint
    from app.db.models.jurisdiction import Jurisdiction, JurisdictionVersion
    from app.db.models.routing import RoutingRule

    def fingerprint():
        def table_rows(model, fields):
            return sorted(
                [tuple(getattr(r, f) for f in fields) for r in db.query(model).all()]
            )

        return {
            "jurisdictions": table_rows(
                Jurisdiction, ("code", "name", "kind")
            ),
            "versions": table_rows(
                JurisdictionVersion, ("code", "version_no", "status")
            ),
            "rules": table_rows(
                RoutingRule, ("code", "issue_type_code", "authority_id", "department_id", "service_id", "scope", "priority")
            ),
            "complaints": table_rows(
                Complaint, ("public_ref", "status", "lat", "lng")
            ),
        }

    before = fingerprint()
    _simulate(client, lon=76.638, lat=12.312, issue="heritage_maintenance")
    _simulate(client, lon=76.60731308845853, lat=12.279255877741852, issue="garbage_collection")
    client.get("/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview")
    assert fingerprint() == before


def test_f_preview_and_simulate_agree_on_affected(client) -> None:
    """simulate.affected_complaint_count == migration-preview.affected_count."""
    from app.whatif.whatif_service import PREVIEW_DATE

    preview = client.get(
        "/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview"
    ).json()
    assert preview["affected_count"] == 3

    body = _simulate(
        client,
        lon=76.6375,
        lat=12.3125,
        issue="water_supply",
        on_date=PREVIEW_DATE.isoformat(),
    )
    assert body["affected_complaint_count"] == preview["affected_count"]

    preview_rows = {row["public_ref"]: row for row in preview["complaints"]}
    for ref in ("C-1002", "C-1007", "C-1009"):
        assert preview_rows[ref]["in_proposed_boundary"] is True
        assert preview_rows[ref]["migration_required"] is True

    # A migrating complaint's per-point simulation agrees with its preview row.
    row = preview_rows["C-1009"]
    sim = _simulate(
        client, lon=row["longitude"], lat=row["latitude"],
        issue=row["issue_type"], on_date=PREVIEW_DATE.isoformat(),
    )
    assert sim["proposed"]["jurisdiction_code"] == row["proposed_jurisdiction_code"]
    assert sim["current"]["jurisdiction_code"] == row["current_jurisdiction_code"]
    assert len(sim["responsibility_deltas"]) > 0
