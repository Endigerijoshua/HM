"""Rule-based complaint scoring (P2 add-on).

Two deterministic, fully explainable heuristics sit alongside the routing
result. Neither uses machine learning: every score is a documented threshold
over integer counts and great-circle distances, and every score carries a
plain-English reason a citizen (or an auditor) can read.

* :func:`calculate_trust_score` - is this report likely genuine, or spam / a
  duplicate filing?
* :func:`calculate_priority` - how urgently should the report be handled?

Both functions are pure: they take a complaint plus a candidate list and return
a :class:`Score`, so they can be unit-tested without a database or clock.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Iterable

# --- tunable, documented constants -----------------------------------------

#: Complaints are only considered a spam/duplicate signal if filed this recently.
RECENT_WINDOW = timedelta(minutes=10)

#: "Same spot, same issue" duplicate radius (metres).
NEAR_DUPLICATE_RADIUS_M = 50.0

#: Cluster radius for the priority score (metres).
CLUSTER_RADIUS_M = 200.0

#: Descriptions shorter than this (after trimming) count as missing detail.
MIN_DESCRIPTION_LENGTH = 5

#: Per-issue-type severity weight: 1 = minor nuisance, 5 = public-health hazard.
#: Unknown codes fall back to :data:`DEFAULT_SEVERITY_WEIGHT`.
SEVERITY_WEIGHTS: dict[str, int] = {
    # water / health hazards
    "sewage": 5,
    "sewage_overflow": 5,
    "water_supply": 4,
    "drainage": 4,
    "drain_cleaning": 3,
    "power_outage": 4,
    # sanitation
    "garbage": 3,
    "garbage_collection": 3,
    "overflowing_bin": 3,
    "illegal_dumping": 3,
    "public_toilet": 3,
    "street_sweeping": 2,
    "construction_waste": 3,
    # roads / highways
    "pothole": 2,
    "road_repair": 2,
    "road_damage": 2,
    "nh_repair": 3,
    "sh_repair": 3,
    # lighting / utility
    "streetlight": 2,
    "street_light": 2,
    # other
    "heritage_maintenance": 2,
    "public_property_damage": 2,
    "layout_approval": 1,
}
DEFAULT_SEVERITY_WEIGHT = 2

#: Human-readable severity band, used only to build the plain-English reason.
_SEVERITY_BANDS: dict[int, str] = {
    5: "public-health hazard",
    4: "high-impact utility issue",
    3: "sanitation issue",
    2: "routine maintenance issue",
    1: "minor administrative issue",
}


@dataclass(frozen=True)
class ComplaintFacts:
    """The minimal complaint shape the scoring functions need.

    A draft (not yet persisted) or a database row both map onto this, so the
    scoring functions never depend on the ORM or the request model.
    """

    latitude: float
    longitude: float
    issue_type: str
    description: str
    source: str
    created_at: datetime
    public_ref: str | None = None

    @classmethod
    def from_orm(cls, row: object) -> "ComplaintFacts":
        """Build facts from a ``Complaint`` ORM row (lat/lng naming)."""
        return cls(
            latitude=float(getattr(row, "lat")),
            longitude=float(getattr(row, "lng")),
            issue_type=str(getattr(row, "issue_type_code")),
            description=str(getattr(row, "description") or ""),
            source=str(getattr(row, "source") or ""),
            created_at=_as_utc(getattr(row, "created_at")),
            public_ref=getattr(row, "public_ref", None),
        )


@dataclass(frozen=True)
class Score:
    """A score level plus the human-readable justification for it."""

    level: str  # "low" | "medium" | "high"
    points: int
    reason: str


def _as_utc(value: datetime | None) -> datetime:
    """Normalise a timestamp to timezone-aware UTC (SQLite stores naive UTC)."""
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two WGS84 points, in metres."""
    radius_m = 6_371_000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lng2 - lng1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * radius_m * asin(sqrt(a))


def _is_same_complaint(a: ComplaintFacts, b: ComplaintFacts) -> bool:
    if a.public_ref is not None and b.public_ref is not None:
        return a.public_ref == b.public_ref
    return a is b


def _within_recent_window(
    complaint: ComplaintFacts,
    candidate: ComplaintFacts,
    window: timedelta,
) -> bool:
    age = complaint.created_at - _as_utc(candidate.created_at)
    return timedelta(0) <= age <= window


def calculate_trust_score(
    complaint: ComplaintFacts,
    recent_complaints: Iterable[ComplaintFacts],
    *,
    window: timedelta = RECENT_WINDOW,
) -> Score:
    """Score how trustworthy a complaint looks, from weak to strong signals.

    Signals (each adds "risk" points; more points = lower trust):

    (a) volume from one source: how many *other* complaints the same
        source/device filed inside ``window`` (1 -> +1, 2-3 -> +2, >=4 -> +3);
    (b) thin description: text trimmed shorter than ``MIN_DESCRIPTION_LENGTH``
        counts as no detail (+2);
    (c) near-duplicate: another recent report of the *same issue* within
        ``NEAR_DUPLICATE_RADIUS_M`` (+2, or +3 when several exist).

    Level thresholds: 0 -> high, 1-2 -> medium, >=3 -> low.
    """
    candidates = list(recent_complaints)
    others = [c for c in candidates if not _is_same_complaint(complaint, c)]
    recent = [c for c in others if _within_recent_window(complaint, c, window)]

    same_source = [c for c in recent if c.source == complaint.source]
    near_dupes = [
        c
        for c in recent
        if c.issue_type == complaint.issue_type
        and haversine_m(
            complaint.latitude, complaint.longitude, c.latitude, c.longitude
        )
        <= NEAR_DUPLICATE_RADIUS_M
    ]

    points = 0
    parts: list[str] = []

    same_source_count = len(same_source)
    if same_source_count >= 4:
        points += 3
    elif same_source_count >= 2:
        points += 2
    elif same_source_count == 1:
        points += 1
    if same_source_count:
        parts.append(
            f"{same_source_count} similar reports in {int(window.total_seconds() // 60)} "
            "minutes from this source"
        )

    if len(complaint.description.strip()) < MIN_DESCRIPTION_LENGTH:
        points += 2
        parts.append("the complaint description is empty or too short")

    duplicate_count = len(near_dupes)
    if duplicate_count >= 2:
        points += 3
        parts.append(
            f"{duplicate_count} near-identical reports within "
            f"{int(NEAR_DUPLICATE_RADIUS_M)} m filed recently"
        )
    elif duplicate_count == 1:
        points += 2
        parts.append(
            f"a near-identical report within {int(NEAR_DUPLICATE_RADIUS_M)} m "
            "was filed recently"
        )

    if points >= 3:
        level = "low"
    elif points >= 1:
        level = "medium"
    else:
        level = "high"

    if parts:
        reason = "Flagged: " + "; ".join(parts) + "."
    else:
        reason = "No duplicate or spam signals detected."
    return Score(level=level, points=points, reason=reason)


def calculate_priority(
    complaint: ComplaintFacts,
    nearby_open_complaints: Iterable[ComplaintFacts],
) -> Score:
    """Score how urgently a complaint should be handled.

    Signals:

    (a) severity weight for the issue type (see :data:`SEVERITY_WEIGHTS`);
    (b) how many *other* open complaints sit within ``CLUSTER_RADIUS_M``
        (a cluster points at a real, shared problem).

    Rules (first match wins, so the reason is always deterministic):

    * high   - severity 5, or >=3 open complaints nearby, or points >= 6;
    * medium - severity >= 3, or any open complaint nearby, or points >= 3;
    * low    - otherwise.

    ``points`` is ``severity + min(nearby, 5)`` for transparency.
    """
    severity = SEVERITY_WEIGHTS.get(complaint.issue_type, DEFAULT_SEVERITY_WEIGHT)

    others = [
        c
        for c in nearby_open_complaints
        if not _is_same_complaint(complaint, c)
    ]
    nearby = [
        c
        for c in others
        if haversine_m(
            complaint.latitude, complaint.longitude, c.latitude, c.longitude
        )
        <= CLUSTER_RADIUS_M
    ]
    nearby_count = len(nearby)
    points = severity + min(nearby_count, 5)

    if severity >= 5 or nearby_count >= 3 or points >= 6:
        level = "high"
    elif severity >= 3 or nearby_count >= 1 or points >= 3:
        level = "medium"
    else:
        level = "low"

    band = _SEVERITY_BANDS.get(severity, "civic issue")
    issue_label = complaint.issue_type.replace("_", " ")
    parts = [f"{issue_label} is a {band} (severity {severity}/5)"]
    if nearby_count:
        parts.append(
            f"{nearby_count} other open complaint(s) within "
            f"{int(CLUSTER_RADIUS_M)} m suggest a cluster problem"
        )
    reason = "; ".join(parts) + "."
    return Score(level=level, points=points, reason=reason)
