"""Focused deterministic P6 tests for the responsibility graph.

The P6 graph router (``app.api.routers.graph``) exposes a single GET:

* ``GET /api/v1/graph/resolve?lat=..&lng=..&issue_type=..&date=..`` -> GraphResolveResponse

The graph is a deterministic projection of the P2 routing decision and never
re-derives routing logic. Node ids are stable (``location:..``, ``jurisdiction:..``,
``authority:..``, ``department:..``, ``service:..``, ``issue:..``, ``escalation:..``)
and edges use exactly ``RESPONSIBLE_FOR | MANAGED_BY | HANDLED_BY | ESCALATES_TO``.
"""
from __future__ import annotations

BASE = "/api/v1/graph/resolve"

HERITAGE_ISSUE = "heritage_maintenance"
HERITAGE_POINT = {"lat": 12.3125, "lng": 76.635}


def _resolve(client, *, lat, lng, issue_type, date):
    response = client.get(
        BASE,
        params={
            "lat": lat,
            "lng": lng,
            "issue_type": issue_type,
            "date": date,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _node_ids(body: dict) -> list[str]:
    return [n["id"] for n in body["nodes"]]


def _edge_chain(body: dict) -> list[tuple[str, str]]:
    """Ordered (node-id, edge-type) transitions along the flow."""
    return [(e["source"], e["type"]) for e in body["edges"]]


def test_graph_resolve_success(client) -> None:
    """Heritage issue resolves fully on 2024-06-01 with an audit id."""
    body = _resolve(
        client,
        lat=HERITAGE_POINT["lat"],
        lng=HERITAGE_POINT["lng"],
        issue_type=HERITAGE_ISSUE,
        date="2024-06-01",
    )
    assert body["status"] == "RESOLVED"
    assert body["date"] == "2024-06-01"
    assert body["issue_type"] == HERITAGE_ISSUE
    assert body["routing_id"] is not None
    assert body["routing_rule_id"] is not None
    assert "inside" in body["explanation"]
    assert "administered by" in body["explanation"]
    assert "handled by" in body["explanation"]
    assert len(body["nodes"]) >= 7
    assert len(body["edges"]) >= 6


def test_graph_node_types(client) -> None:
    """A resolved graph carries every node type of the chain."""
    body = _resolve(
        client,
        lat=HERITAGE_POINT["lat"],
        lng=HERITAGE_POINT["lng"],
        issue_type=HERITAGE_ISSUE,
        date="2024-06-01",
    )
    types = {n["type"] for n in body["nodes"]}
    assert types == {
        "LOCATION",
        "JURISDICTION",
        "AUTHORITY",
        "DEPARTMENT",
        "SERVICE",
        "ISSUE",
        "ESCALATION",
    }
    authority = next(n for n in body["nodes"] if n["type"] == "AUTHORITY")
    assert authority["id"] == "authority:A-MCC"
    assert authority["label"]
    jurisdiction = next(n for n in body["nodes"] if n["type"] == "JURISDICTION")
    assert jurisdiction["id"] == "jurisdiction:W-05"


def test_graph_edge_chain(client) -> None:
    """Location → Jurisdiction → Authority → Department → Service → Issue → Escalation."""
    body = _resolve(
        client,
        lat=HERITAGE_POINT["lat"],
        lng=HERITAGE_POINT["lng"],
        issue_type=HERITAGE_ISSUE,
        date="2024-06-01",
    )
    ids = _node_ids(body)
    assert ids[0] == "location:76.63500,12.31250"
    assert ids[-1] == "escalation:1"

    by_id = {n["id"]: n for n in body["nodes"]}
    for edge in body["edges"]:
        assert edge["source"] in by_id
        assert edge["target"] in by_id

    types = sorted(e["type"] for e in body["edges"])
    assert types == [
        "ESCALATES_TO",
        "HANDLED_BY",
        "HANDLED_BY",
        "MANAGED_BY",
        "MANAGED_BY",
        "RESPONSIBLE_FOR",
    ]
    chain = [e["type"] for e in body["edges"]]
    assert chain[:5] == [
        "RESPONSIBLE_FOR",
        "MANAGED_BY",
        "MANAGED_BY",
        "HANDLED_BY",
        "HANDLED_BY",
    ]
    assert chain[5] == "ESCALATES_TO"
    assert all(e["label"] for e in body["edges"])


def test_graph_unresolved_responsibility(client) -> None:
    """Construction waste at C-1002 ties; the graph stops at the jurisdiction."""
    body = _resolve(
        client,
        lat=12.3125,
        lng=76.6375,
        issue_type="construction_waste",
        date="2024-06-01",
    )
    assert body["status"] == "RESPONSIBILITY_UNRESOLVED"
    assert "jurisdiction:W-05" in _node_ids(body)
    types = {n["type"] for n in body["nodes"]}
    assert "AUTHORITY" not in types
    assert "DEPARTMENT" not in types
    assert "SERVICE" not in types
    assert "ESCALATION" not in types
    # The chain stays connected: jurisdiction → issue with no settled authority.
    jur_to_issue = [e for e in body["edges"] if e["target"].startswith("issue:")]
    assert len(jur_to_issue) == 1
    assert jur_to_issue[0]["type"] == "RESPONSIBLE_FOR"
    assert "tie" in body["explanation"]


def test_graph_no_jurisdiction_gap(client) -> None:
    """Street-light at C-1004 has no jurisdiction; only location + issue remain."""
    body = _resolve(
        client,
        lat=12.265,
        lng=76.632,
        issue_type="street_light",
        date="2024-06-01",
    )
    assert body["status"] == "NO_JURISDICTION"
    types = {n["type"] for n in body["nodes"]}
    assert types == {"LOCATION", "ISSUE"}
    assert all(e["type"] == "RESPONSIBLE_FOR" for e in body["edges"])
    assert body["edges"][0]["source"].startswith("location:")
    assert body["edges"][0]["target"].startswith("issue:")


def test_graph_temporal_jurisdiction_change(client) -> None:
    """The same point+issue graph changes between the 2020 and 2024 sets."""
    v1 = _resolve(
        client,
        lat=HERITAGE_POINT["lat"],
        lng=HERITAGE_POINT["lng"],
        issue_type=HERITAGE_ISSUE,
        date="2023-06-01",
    )
    v2 = _resolve(
        client,
        lat=HERITAGE_POINT["lat"],
        lng=HERITAGE_POINT["lng"],
        issue_type=HERITAGE_ISSUE,
        date="2024-06-01",
    )
    assert v1["status"] == "RESPONSIBILITY_UNRESOLVED"
    assert v2["status"] == "RESOLVED"
    # Same jurisdiction W-05 both times, but the responsibility chain changed:
    # V1 has no settled actor, V2 carries the full actor chain + escalation.
    assert "jurisdiction:W-05" in _node_ids(v1)
    assert "jurisdiction:W-05" in _node_ids(v2)
    v1_types = {n["type"] for n in v1["nodes"]}
    v2_types = {n["type"] for n in v2["nodes"]}
    assert "AUTHORITY" not in v1_types
    assert "AUTHORITY" in v2_types
    assert "ESCALATION" not in v1_types
    assert "ESCALATION" in v2_types
    assert v2["explanation"] != v1["explanation"]


def test_graph_deterministic_repeated_response(client) -> None:
    """Same inputs produce identical nodes, edges and explanation.

    Only ``routing_id`` (the underlying P2 audit row) is unique per resolve —
    every decision is still audited, exactly like ``/routing/resolve``.
    """
    first = _resolve(
        client,
        lat=HERITAGE_POINT["lat"],
        lng=HERITAGE_POINT["lng"],
        issue_type=HERITAGE_ISSUE,
        date="2024-06-01",
    )
    second = _resolve(
        client,
        lat=HERITAGE_POINT["lat"],
        lng=HERITAGE_POINT["lng"],
        issue_type=HERITAGE_ISSUE,
        date="2024-06-01",
    )
    assert first["status"] == second["status"] == "RESOLVED"
    assert first["nodes"] == second["nodes"]
    assert first["edges"] == second["edges"]
    assert first["explanation"] == second["explanation"]
    assert first["date"] == second["date"]
    assert first["routing_id"] is not None
    assert second["routing_id"] is not None