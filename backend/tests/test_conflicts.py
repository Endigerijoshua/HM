"""Focused deterministic P5 tests for the responsibility conflict detector.

The P5 conflicts router (``app.api.routers.conflicts``) exposes:

* ``GET  /api/v1/conflicts``            -> ``ConflictListResponse``
* ``GET  /api/v1/conflicts/{id}``       -> ``ConflictResponse``
* ``POST /api/v1/conflicts/detect``     -> ``ConflictDetectResponse``

Every assertion is deterministic against the seeded dataset. ``detect`` is the
only mutating endpoint (it persists *new* conflicts). Each test that runs it
cleans up its own rows afterwards via the ``detect_run`` fixture so the shared
session-scoped database always returns to the seeded ``responsibility_conflicts
== 1`` count before ``test_seed`` runs (files execute alphabetically).
"""
from __future__ import annotations

import pytest

from app.db.models.complaints import Complaint
from app.db.models.conflicts import ResponsibilityConflict

BASE = "/api/v1/conflicts"


@pytest.fixture()
def detect_run(client, db):
    """Run POST /conflicts/detect via the API and clean its rows up after."""
    created: list[str] = []

    def run() -> dict:
        body = client.post(f"{BASE}/detect").json()
        created.extend(item["conflict_id"] for item in body.get("conflicts", []))
        return body

    yield run

    if created:
        rows = (
            db.query(ResponsibilityConflict)
            .filter(ResponsibilityConflict.code.in_(created))
            .all()
        )
        for row in rows:
            db.delete(row)
        db.commit()


def _by_type(body: dict, conflict_type: str) -> list[dict]:
    return [
        c
        for c in body["conflicts"]
        if c["conflict_type"] == conflict_type
    ]


def _for_ref(body: dict, conflict_type: str, ref: str) -> dict:
    matches = [
        c
        for c in _by_type(body, conflict_type)
        if c.get("complaint_ref") == ref
    ]
    assert len(matches) == 1, f"expected exactly one {conflict_type} for {ref}"
    return matches[0]


def test_detect_authority_mismatch(detect_run) -> None:
    """C-1003 (geo A-MCC vs routed A-NHAI) and C-1008 (geo A-MCC vs routed A-CESC)."""
    body = detect_run()

    nh = _for_ref(body, "AUTHORITY_MISMATCH", "C-1003")
    assert nh["severity"] == "HIGH"
    assert nh["status"] == "OPEN"
    assert nh["date"] == "2024-06-01"
    assert nh["expected_authority"]["code"] == "A-MCC"
    assert nh["routed_authority"]["code"] == "A-NHAI"
    assert nh["jurisdiction_code"] is not None
    assert nh["issue_type"] == "nh_repair"
    assert nh["explanation"]
    assert nh["created_at"]

    power = _for_ref(body, "AUTHORITY_MISMATCH", "C-1008")
    assert power["severity"] == "HIGH"
    assert power["expected_authority"]["code"] == "A-MCC"
    assert power["routed_authority"]["code"] == "A-CESC"
    assert power["issue_type_name"] == "Electricity outage"


def test_detect_department_and_service_mismatch(detect_run) -> None:
    """construction_waste at C-1002 ties RULE-CW-DEV (RI/ROAD) vs RULE-CW-SAN (HS/GARBAGE)."""
    body = detect_run()

    gap = _for_ref(body, "RESPONSIBILITY_GAP", "C-1002")
    assert gap["severity"] == "HIGH"
    assert gap["expected_department"]["code"] == "MCC-D-RI"
    assert gap["routed_department"]["code"] == "MCC-D-HS"
    assert gap["expected_service"]["code"] == "SVC-ROAD"
    assert gap["routed_service"]["code"] == "SVC-GARBAGE"

    dept = _for_ref(body, "DEPARTMENT_MISMATCH", "C-1002")
    assert dept["severity"] == "MEDIUM"
    assert dept["expected_department"]["code"] == "MCC-D-RI"
    assert dept["routed_department"]["code"] == "MCC-D-HS"
    assert dept["expected_authority"]["code"] == "A-MCC"

    svc = _for_ref(body, "SERVICE_MISMATCH", "C-1002")
    assert svc["severity"] == "MEDIUM"
    assert svc["expected_service"]["code"] == "SVC-ROAD"
    assert svc["routed_service"]["code"] == "SVC-GARBAGE"


def test_detect_temporal_rule_conflict(detect_run) -> None:
    """power_outage at C-1008: none on 2024-03-15, A-CESC on 2024-06-01."""
    body = detect_run()

    conflict = _for_ref(body, "TEMPORAL_RULE_CONFLICT", "C-1008")
    assert conflict["severity"] == "MEDIUM"
    assert conflict["date"] == "2024-03-15"
    assert conflict["routed_authority"]["code"] == "A-CESC"
    assert conflict["jurisdiction_code"] is not None
    assert "DELIM-2020" in conflict["explanation"]
    assert "DELIM-2024" in conflict["explanation"]


def test_detect_responsibility_gap_no_jurisdiction(detect_run) -> None:
    """C-1004 (street_light, OPEN) has no containing jurisdiction on any set."""
    body = detect_run()

    gap = _for_ref(body, "RESPONSIBILITY_GAP", "C-1004")
    assert gap["severity"] == "HIGH"
    assert gap["jurisdiction_code"] is None
    assert gap["jurisdiction_name"] is None
    assert gap["expected_authority"] is None
    assert gap["routed_authority"] is None
    assert gap["issue_type"] == "street_light"


def test_detect_no_false_conflicts(detect_run) -> None:
    """Complaints fully settled by the MCC see no spurious conflict rows."""
    body = detect_run()

    refs = {c["complaint_ref"] for c in body["conflicts"]}
    assert refs == {"C-1002", "C-1003", "C-1004", "C-1008"}
    assert all(
        ref not in refs
        for ref in ("C-1001", "C-1005", "C-1006", "C-1007", "C-1009")
    )


def test_detect_is_deterministic_and_idempotent(client, detect_run) -> None:
    """Repeat detection creates nothing new and keeps the full set stable."""
    first = detect_run()
    assert first["created"] == 7
    assert first["evaluated"] == 9
    assert first["count"] == 7
    first_ids = {c["conflict_id"] for c in first["conflicts"]}
    assert len(first_ids) == 7

    listed = client.get(BASE).json()
    assert listed["count"] == 8  # 7 detected + seeded CF-1001
    assert all(cid in {c["conflict_id"] for c in listed["conflicts"]} for cid in first_ids)

    second = detect_run()
    assert second["created"] == 0
    assert second["conflicts"] == []

    listed_again = client.get(BASE).json()
    assert listed_again["count"] == 8
    assert {c["conflict_id"] for c in listed_again["conflicts"]} == {
        c["conflict_id"] for c in listed["conflicts"]
    }


def test_list_conflicts_keeps_seed_cf1001(client, detect_run) -> None:
    """detect never mutates the seeded GEO_VS_SERVICE conflict."""
    detect_run()
    listed = client.get(BASE).json()
    assert listed["count"] == 8

    seeded = next(c for c in listed["conflicts"] if c["conflict_id"] == "CF-1001")
    assert seeded["conflict_type"] == "GEO_VS_SERVICE"
    assert seeded["status"] == "OPEN"

    open_only = client.get(f"{BASE}?status=OPEN").json()
    assert open_only["count"] == 8


def test_get_conflict_by_id(detect_run) -> None:
    """GET /conflicts/{conflict_id} returns the created or seeded record."""
    body = detect_run()
    sample = body["conflicts"][0]
    got = client_get(sample["conflict_id"])
    assert got.status_code == 200
    assert got.json()["conflict_id"] == sample["conflict_id"]


def client_get(conflict_id: str):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        return c.get(f"{BASE}/{conflict_id}")


def test_get_conflict_not_found(client) -> None:
    resp = client.get(f"{BASE}/CF-DOES-NOT-EXIST")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_detect_readonly_on_complaints(db, detect_run) -> None:
    """detect persists conflict rows only; complaints stay untouched."""
    before = db.query(Complaint).count()
    detect_run()
    after = db.query(Complaint).count()
    assert after == before == 9