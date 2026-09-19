"""Focused deterministic P4 tests for the complaint migration preview.

The P4 read-only preview evaluates every OPEN complaint against a proposed
scenario boundary (``GET /api/v1/whatif/scenarios/{code}/migration-preview``)
and reports, per complaint, the live (current) responsibility vs the
heritage-precinct responsibility the proposed boundary implies.

These assertions are fully deterministic against the seeded data:

* OPEN complaints: C-1002, C-1007 and C-1009 sit inside the ``SC-V3-REZONE``
  boundary; C-1001 (flip point), C-1003, C-1004 and C-1008 are outside.
* C-1002 (water) and C-1007 (road) move from their live MCC departments to
  the heritage precinct => ``migration_required``.
* C-1009 is inside and already under the heritage department/service, but its
  live jurisdiction is the W-05 ward => jurisdiction changes to ``HER-01``,
  so it also migrates => ``affected_count == 3``.
* C-1005 / C-1006 are not OPEN and never appear.
* The preview never mutates jurisdictions or complaints.
"""
from __future__ import annotations


def _by_ref(payload: dict) -> dict:
    return {item["public_ref"]: item for item in payload["complaints"]}


def test_migration_preview_flags_expected_complaints(client) -> None:
    resp = client.get(
        "/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["scenario_code"] == "SC-V3-REZONE"
    assert body["total_open_complaints"] == 7
    assert body["affected_count"] == 3

    rows = _by_ref(body)
    assert set(rows) == {
        "C-1001", "C-1002", "C-1003", "C-1004",
        "C-1007", "C-1008", "C-1009",
    }

    assert rows["C-1002"]["in_proposed_boundary"] is True
    assert rows["C-1002"]["migration_required"] is True
    assert rows["C-1002"]["current_department_code"] == "MCC-D-WS"
    assert rows["C-1002"]["proposed_department_code"] == "MCC-D-HP"
    assert rows["C-1002"]["proposed_jurisdiction_code"] == "HER-01"

    assert rows["C-1007"]["in_proposed_boundary"] is True
    assert rows["C-1007"]["migration_required"] is True
    assert rows["C-1007"]["current_department_code"] == "MCC-D-RI"
    assert rows["C-1007"]["proposed_service_code"] == "SVC-HERITAGE"

    assert rows["C-1009"]["in_proposed_boundary"] is True
    assert rows["C-1009"]["migration_required"] is True
    assert rows["C-1009"]["current_department_code"] == "MCC-D-HP"
    assert rows["C-1009"]["current_jurisdiction_code"] == "W-05"
    assert rows["C-1009"]["proposed_jurisdiction_code"] == "HER-01"

    for ref in ("C-1001", "C-1003", "C-1004", "C-1008"):
        assert rows[ref]["in_proposed_boundary"] is False
        assert rows[ref]["migration_required"] is False
        assert rows[ref]["proposed_department_code"] == rows[ref]["current_department_code"]


def test_migration_preview_contains_required_fields(client) -> None:
    body = client.get(
        "/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview"
    ).json()
    item = _by_ref(body)["C-1002"]
    assert item["complaint_id"] == 2
    assert item["public_ref"] == "C-1002"
    assert item["issue_type"] == "water_supply"
    assert item["latitude"] == 12.3125
    assert item["longitude"] == 76.6375
    assert item["current_ward_code"]
    assert item["current_authority_code"] == "A-MCC"
    assert item["current_department_code"] == "MCC-D-WS"
    assert item["proposed_ward_code"]
    assert item["proposed_authority_code"] == "A-MCC"
    assert item["proposed_department_code"] == "MCC-D-HP"
    assert item["migration_required"] is True
    assert item["explanation"]


def test_migration_preview_unknown_scenario_404(client) -> None:
    resp = client.get("/api/v1/whatif/scenarios/SC-NOPE/migration-preview")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_migration_preview_is_deterministic_and_read_only(client, db) -> None:
    from app.db.models.complaints import Complaint
    from app.db.models.jurisdiction import Jurisdiction

    before_jurisdictions = [
        (j.code, j.name, j.kind)
        for j in db.query(Jurisdiction).order_by(Jurisdiction.code)
    ]
    before_complaints = [
        (c.public_ref, c.status, c.lat, c.lng)
        for c in db.query(Complaint).order_by(Complaint.id)
    ]

    first = client.get(
        "/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview"
    ).json()
    second = client.get(
        "/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview"
    ).json()
    assert first == second

    after_jurisdictions = [
        (j.code, j.name, j.kind)
        for j in db.query(Jurisdiction).order_by(Jurisdiction.code)
    ]
    after_complaints = [
        (c.public_ref, c.status, c.lat, c.lng)
        for c in db.query(Complaint).order_by(Complaint.id)
    ]
    assert after_jurisdictions == before_jurisdictions
    assert after_complaints == before_complaints


def test_migration_preview_disregards_closed_complaints(client) -> None:
    body = client.get(
        "/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview"
    ).json()
    refs = {item["public_ref"] for item in body["complaints"]}
    assert "C-1005" not in refs  # IN_PROGRESS
    assert "C-1006" not in refs  # RESOLVED


def test_whatif_simulate_count_agrees_with_preview(client) -> None:
    """simulate().affected_complaint_count always equals the preview count.

    Both callers evaluate the same OPEN-complaint set against the same stored
    scenario boundary, so the what-if affected count and the migration-preview
    affected count are identical for a given scenario and date.
    """
    from app.whatif.whatif_service import PREVIEW_DATE

    preview = client.get(
        "/api/v1/whatif/scenarios/SC-V3-REZONE/migration-preview"
    ).json()

    resp = client.post("/api/v1/whatif/simulate", json={
        "longitude": 76.6375,
        "latitude": 12.3125,
        "issue_type_code": "water_supply",
        "on_date": PREVIEW_DATE.isoformat(),
    })
    assert resp.status_code == 200, resp.text
    sim = resp.json()
    assert sim["scenario_code"] == "SC-V3-REZONE"
    assert sim["affected_complaint_count"] == preview["affected_count"] == 3
    assert sim["affected_complaint_count"] == preview["total_open_complaints"] - 4