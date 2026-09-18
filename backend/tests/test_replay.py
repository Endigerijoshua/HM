"""Focused deterministic P7 tests for the historical jurisdiction replay API.

The replay endpoint reuses the P2 routing service — each sampled day is an
independent ``/routing/resolve``-style resolution — and merges identical
consecutive outcomes into periods, so a single coordinate can be walked across
dates and boundary transitions (jurisdiction/version/rule changes, gaps and
unresolved responsibility) appear explicitly. Replay never commits, so it never
writes audit rows.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models.audit import AuditLog

BASE = "/api/v1/replay/point"

# Deterministic seeded geometry (see README "Demo / seed data").
# The seed computes the "flip coordinate" deterministically
# (``app.seed.seed_runner._flip_coords``): its covering grid cell differs between
# the V1 and V2 mosaics. Under the current seed it keeps ward W-01 in both
# versions but switches boundary version (DELIM-2020 → DELIM-2024) and routing
# rule (RULE-GARBAGE-PRE2024 → RULE-GARBAGE-01), with a NO_JURISDICTION gap.
FLIP_LNG, FLIP_LAT = 76.60731308845853, 12.279255877741852
HERITAGE_LNG, HERITAGE_LAT = 76.635, 12.3125   # W-05; heritage rule starts 2024-04-01
CW_LNG, CW_LAT = 76.6375, 12.3125              # C-1002 coords; construction-waste tie


def _replay(
    client: TestClient,
    *,
    lat: float,
    lng: float,
    issue: str,
    start: str,
    end: str,
) -> dict:
    response = client.get(
        BASE,
        params={
            "latitude": lat,
            "longitude": lng,
            "issue_type": issue,
            "start_date": start,
            "end_date": end,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_replay_normal_historical_lookup(client) -> None:
    """A single stable range collapses into one fully-resolved period."""
    body = _replay(
        client,
        lat=FLIP_LAT,
        lng=FLIP_LNG,
        issue="garbage_collection",
        start="2023-06-01",
        end="2023-06-05",
    )
    assert body["status"] == "REPLAY_OK"
    assert body["day_count"] == 4
    assert body["period_count"] == 1
    assert body["jurisdiction_change_count"] == 0

    period = body["periods"][0]
    assert period["effective_from"] == "2023-06-01"
    assert period["effective_to"] == "2023-06-05"
    assert period["boundary_change"] is False
    assert period["status"] == "RESOLVED"
    assert period["jurisdiction_code"] == "W-01"
    assert period["jurisdiction_kind"] == "WARD"
    assert period["version_code"] == "DELIM-2020"
    assert period["authority"]["code"] == "A-MCC"
    assert period["department"]["code"] == "MCC-D-HS"
    assert period["service"]["code"] == "SVC-GARBAGE"
    assert period["routing_rule_code"] == "RULE-GARBAGE-PRE2024"
    assert period["explanation"]
    assert period["chain"] == "W-01 → A-MCC → MCC-D-HS"


def test_replay_boundary_transition_flip_point(client) -> None:
    """Focused: the SAME coordinate resolves under different boundary versions
    when its date crosses the V1→V2 change (with an explicit no-jurisdiction
    gap), switching boundary version and routing rule deterministically."""
    body = _replay(
        client,
        lat=FLIP_LAT,
        lng=FLIP_LNG,
        issue="garbage_collection",
        start="2023-06-01",
        end="2024-06-01",
    )
    assert body["period_count"] == 3
    assert body["jurisdiction_change_count"] == 2

    v1, gap, v2 = body["periods"]
    assert (v1["effective_from"], v1["effective_to"]) == ("2023-06-01", "2023-12-31")
    assert v1["status"] == "RESOLVED"
    assert v1["version_code"] == "DELIM-2020"
    assert v1["routing_rule_code"] == "RULE-GARBAGE-PRE2024"
    assert v1["boundary_change"] is False

    assert (gap["effective_from"], gap["effective_to"]) == ("2023-12-31", "2024-04-01")
    assert gap["status"] == "NO_JURISDICTION"
    assert gap["jurisdiction_code"] is None
    assert gap["authority"] is None
    assert gap["boundary_change"] is True
    assert gap["chain"] == "(no jurisdiction)"

    assert (v2["effective_from"], v2["effective_to"]) == ("2024-04-01", "2024-06-01")
    assert v2["status"] == "RESOLVED"
    assert v2["version_code"] == "DELIM-2024"
    assert v2["routing_rule_code"] == "RULE-GARBAGE-01"
    assert v2["boundary_change"] is True

    # Boundary versions and rules differ; the no-jurisdiction gap is explicit.
    versions = [p["version_code"] for p in body["periods"]]
    assert versions == ["DELIM-2020", None, "DELIM-2024"]
    codes = [p["jurisdiction_code"] for p in body["periods"]]
    assert codes == ["W-01", None, "W-01"]


def test_replay_boundary_transition_responsibility(client) -> None:
    """The same heritage point flips from unresolved responsibility (V1, no rule)
    to the MCC Heritage & Public Works chain (V2 + RULE-HERITAGE-01)."""
    body = _replay(
        client,
        lat=HERITAGE_LAT,
        lng=HERITAGE_LNG,
        issue="heritage_maintenance",
        start="2023-06-01",
        end="2024-05-01",
    )
    assert body["period_count"] == 3

    v1, gap, v2 = body["periods"]
    assert v1["status"] == "RESPONSIBILITY_UNRESOLVED"
    assert v1["jurisdiction_code"] == "W-05"
    assert v1["version_code"] == "DELIM-2020"
    assert v1["authority"] is None
    assert v1["chain"] == "W-05 → (unresolved)"

    assert gap["status"] == "NO_JURISDICTION"

    assert v2["status"] == "RESOLVED"
    assert v2["jurisdiction_code"] == "W-05"
    assert v2["version_code"] == "DELIM-2024"
    assert v2["authority"]["code"] == "A-MCC"
    assert v2["department"]["code"] == "MCC-D-HP"
    assert v2["service"]["code"] == "SVC-HERITAGE"
    assert v2["routing_rule_code"] == "RULE-HERITAGE-01"
    assert v2["chain"] == "W-05 → A-MCC → MCC-D-HP"

    # The responsibility chain is materially different across the boundary.
    assert (v1["authority"], v1["department"]) != (v2["authority"], v2["department"])


def test_replay_invalid_date_range(client) -> None:
    """end_date before start_date is a clear 400; an empty window is valid."""
    response = client.get(
        BASE,
        params={
            "latitude": FLIP_LAT,
            "longitude": FLIP_LNG,
            "issue_type": "garbage_collection",
            "start_date": "2024-06-01",
            "end_date": "2023-06-01",
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_DATE_RANGE"

    empty = _replay(
        client,
        lat=FLIP_LAT,
        lng=FLIP_LNG,
        issue="garbage_collection",
        start="2024-06-01",
        end="2024-06-01",
    )
    assert empty["day_count"] == 0
    assert empty["period_count"] == 0
    assert empty["periods"] == []


def test_replay_no_jurisdiction(client) -> None:
    """Inside the V1→V2 gap the same point has no jurisdiction at all."""
    body = _replay(
        client,
        lat=FLIP_LAT,
        lng=FLIP_LNG,
        issue="garbage_collection",
        start="2024-02-01",
        end="2024-02-10",
    )
    assert body["period_count"] == 1
    period = body["periods"][0]
    assert period["status"] == "NO_JURISDICTION"
    assert period["jurisdiction_code"] is None
    assert period["version_code"] is None
    assert period["chain"] == "(no jurisdiction)"


def test_replay_unresolved_responsibility(client) -> None:
    """Construction waste in W-05 (V2) ties: responsibility cannot be settled."""
    body = _replay(
        client,
        lat=CW_LAT,
        lng=CW_LNG,
        issue="construction_waste",
        start="2024-06-01",
        end="2024-06-08",
    )
    assert body["period_count"] == 1
    period = body["periods"][0]
    assert period["status"] == "RESPONSIBILITY_UNRESOLVED"
    assert period["jurisdiction_code"] == "W-05"
    assert period["version_code"] == "DELIM-2024"
    assert period["authority"] is None
    assert set(period["conflict_rule_codes"]) == {"RULE-CW-DEV", "RULE-CW-SAN"}
    assert period["chain"] == "W-05 → (unresolved)"


def test_replay_deterministic_and_read_only(client, db) -> None:
    """Identical inputs yield byte-identical output and add no audit rows."""
    params = {
        "latitude": FLIP_LAT,
        "longitude": FLIP_LNG,
        "issue_type": "garbage_collection",
        "start_date": "2023-06-01",
        "end_date": "2024-06-01",
    }
    db.expire_all()
    rows_before = db.query(AuditLog).count()

    first = client.get(BASE, params=params)
    second = client.get(BASE, params=params)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json() == second.json()

    db.expire_all()
    rows_after = db.query(AuditLog).count()
    # Replay resolves hundreds of days through P2 routing but never commits:
    # the audit log must be unchanged (strictly read-only).
    assert rows_after == rows_before