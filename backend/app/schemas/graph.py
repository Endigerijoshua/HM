"""Pydantic schemas for the responsibility graph API (P6).

The graph is a deterministic *explanatory view* over the P2 routing result —
it never stores anything and never re-derives routing decisions. Nodes carry a
stable id, a typespace and a human-readable label; edges carry one of the four
roles ``RESPONSIBLE_FOR | MANAGED_BY | HANDLED_BY | ESCALATES_TO``.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

# Node types.
LOCATION = "LOCATION"
JURISDICTION = "JURISDICTION"
AUTHORITY = "AUTHORITY"
DEPARTMENT = "DEPARTMENT"
SERVICE = "SERVICE"
ISSUE = "ISSUE"
ESCALATION = "ESCALATION"

# Edge types.
RESPONSIBLE_FOR = "RESPONSIBLE_FOR"
MANAGED_BY = "MANAGED_BY"
HANDLED_BY = "HANDLED_BY"
ESCALATES_TO = "ESCALATES_TO"


class GraphNode(BaseModel):
    """A single step in the responsibility chain."""

    id: str
    type: str
    label: str


class GraphEdge(BaseModel):
    """A directed relation between two responsibility-chain nodes."""

    id: str
    source: str
    target: str
    type: str
    label: str | None = None


class GraphResolveResponse(BaseModel):
    """Deterministic responsibility chain for one location+issue+date."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    latitude: float
    longitude: float
    issue_type: str
    # Wire key is "date"; the Python attribute is "on_date" (consistent with
    # the P2 routing request schema).
    on_date: date = Field(alias="date")
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    # P2 audit id of the underlying routing decision, when available.
    routing_id: int | None = None
    routing_rule_id: int | None = None
    explanation: str