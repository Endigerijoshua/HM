"""Temporal jurisdiction resolution engine.

Selects the correct jurisdiction for a (longitude, latitude, date) triple using
closed-open validity intervals ``[effective_from, effective_to)``. The engine
never mutates data and never "fixes" overlapping history silently — overlaps
are surfaced as ``TEMPORAL_CONFLICT`` so bad data is visible, not guessed.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from itertools import combinations

from shapely.geometry import Point

from app.db.models.jurisdiction import Area, Jurisdiction, JurisdictionVersion, Road, Ward
from app.gis.base import GeometryProvider, sort_for_display
from app.gis.crs import is_valid_coordinate
from app.schemas.gis import (
    AreaRef,
    CorridorRef,
    JurisdictionLookupResult,
    JurisdictionRef,
    JurisdictionVersionRef,
    LookupStatus,
    TemporalOverlapReport,
    WardRef,
)


class TemporalJurisdictionEngine:
    """Resolves point+date lookups against versioned jurisdiction geometry."""

    def __init__(self, provider: GeometryProvider) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # primary lookup
    # ------------------------------------------------------------------

    def resolve_jurisdiction_at_point(
        self, longitude: float, latitude: float, on_date: date
    ) -> JurisdictionLookupResult:
        """Resolve the jurisdiction(s) governing a point on a date.

        Result classification
        ---------------------
        * ``MATCHED`` - exactly one jurisdiction per (code, kind) contains the point.
        * ``NO_JURISDICTION`` - no active jurisdiction covers the point that date.
        * ``INVALID_COORDINATES`` - the point is outside WGS84 bounds.
        * ``INVALID_GEOMETRY`` - an active jurisdiction's geometry failed to decode.
        * ``TEMPORAL_CONFLICT`` - 2+ active jurisdictions of the same code/kind
          claim the point simultaneously (data integrity problem).
        """
        if not is_valid_coordinate(longitude, latitude):
            return JurisdictionLookupResult(
                status=LookupStatus.INVALID_COORDINATES,
                on_date=on_date,
                lat=latitude,
                lng=longitude,
                message=(
                    f"Coordinates ({longitude}, {latitude}) are out of WGS84 range: "
                    "lng in [-180, 180], lat in [-90, 90]"
                ),
            )

        active = self._provider.jurisdictions_active_on(on_date)
        if not active:
            return JurisdictionLookupResult(
                status=LookupStatus.NO_JURISDICTION,
                on_date=on_date,
                lat=latitude,
                lng=longitude,
                message=f"No jurisdiction version was in force on {on_date.isoformat()}",
            )

        point = Point(longitude, latitude)
        containing = []
        for jurisdiction in active:
            try:
                geometry = self._provider.geometry_for(jurisdiction)
            except Exception:  # noqa: BLE001 - surface decode failures as a status
                return JurisdictionLookupResult(
                    status=LookupStatus.INVALID_GEOMETRY,
                    on_date=on_date,
                    lat=latitude,
                    lng=longitude,
                    message=f"Could not decode geometry for jurisdiction {jurisdiction.code}",
                )
            if geometry.covers(point):
                containing.append(jurisdiction)

        if not containing:
            return JurisdictionLookupResult(
                status=LookupStatus.NO_JURISDICTION,
                on_date=on_date,
                lat=latitude,
                lng=longitude,
                message=f"No jurisdiction covers ({longitude}, {latitude}) on {on_date.isoformat()}",
            )

        grouped: dict[tuple[str, str], list[Jurisdiction]] = defaultdict(list)
        for jurisdiction in containing:
            grouped[(jurisdiction.kind, jurisdiction.code)].append(jurisdiction)
        conflicts = [rows for rows in grouped.values() if len(rows) > 1]
        if conflicts:
            for rows in conflicts:
                rows.sort(key=lambda j: (j.effective_from, j.id))
            conflicting_rows = [j for rows in conflicts for j in rows]
            message = (
                "Temporal overlap: multiple active jurisdictions of the same "
                "code/kind contain the point on "
                f"{on_date.isoformat()}: "
                + ", ".join(
                    f"{r.kind} {r.code} (version {r.version.code}, {r.effective_from}"
                    f"{'' if r.effective_to is None else ' to ' + r.effective_to.isoformat()})"
                    for r in conflicting_rows
                )
            )
            return self._build_result(
                status=LookupStatus.TEMPORAL_CONFLICT,
                on_date=on_date,
                longitude=longitude,
                latitude=latitude,
                message=message,
                jurisdiction=sort_for_display(containing)[0],
            )

        jurisdiction = sort_for_display(containing)[0]
        return self._build_result(
            status=LookupStatus.MATCHED,
            on_date=on_date,
            longitude=longitude,
            latitude=latitude,
            jurisdiction=jurisdiction,
        )

    # ------------------------------------------------------------------
    # supporting lookups (ward / area / road)
    # ------------------------------------------------------------------

    def ward_for(self, jurisdiction: Jurisdiction) -> Ward | None:
        return self._provider.ward_for(jurisdiction)

    def area_at(self, longitude: float, latitude: float, on_date: date) -> Area | None:
        return self._provider.area_at(longitude, latitude, on_date)

    def road_at(self, longitude: float, latitude: float, on_date: date) -> Road | None:
        return self._provider.road_at(longitude, latitude, on_date)

    # ------------------------------------------------------------------
    # data-integrity tooling
    # ------------------------------------------------------------------

    def detect_temporal_overlaps(self, on_date: date | None = None) -> list[TemporalOverlapReport]:
        """Report versioned jurisdictions whose validity windows overlap.

        With ``on_date`` given the report covers jurisdictions co-active that day;
        without a date every overlapping (code, kind) group is reported.
        """
        if on_date is not None:
            rows = self._provider.jurisdictions_active_on(on_date)
        else:
            rows = self._provider.all_jurisdictions()

        grouped: dict[tuple[str, str], list[Jurisdiction]] = defaultdict(list)
        for jurisdiction in rows:
            grouped[(jurisdiction.kind, jurisdiction.code)].append(jurisdiction)

        reports: list[TemporalOverlapReport] = []
        for (kind, code), members in sorted(grouped.items()):
            if len(members) <= 1:
                continue
            overlapping = set()
            for a, b in combinations(members, 2):
                if _windows_overlap(a.effective_from, a.effective_to, b.effective_from, b.effective_to):
                    overlapping.add(a.id)
                    overlapping.add(b.id)
            if not overlapping:
                continue
            involved = [m for m in members if m.id in overlapping]
            reports.append(
                TemporalOverlapReport(
                    kind=kind,
                    code=code,
                    count=len(involved),
                    jurisdiction_ids=[m.id for m in involved],
                    version_ids=sorted({m.jurisdiction_version_id for m in involved}),
                    effective_windows=[
                        {
                            "jurisdiction_id": m.id,
                            "effective_from": m.effective_from.isoformat(),
                            "effective_to": m.effective_to.isoformat() if m.effective_to else None,
                        }
                        for m in involved
                    ],
                )
            )
        return reports

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _build_result(
        self,
        *,
        status: LookupStatus,
        on_date: date,
        longitude: float,
        latitude: float,
        message: str | None = None,
        jurisdiction: Jurisdiction | None = None,
    ) -> JurisdictionLookupResult:
        ward: Ward | None = None
        areas: list[Area] = []
        road: Road | None = None

        if jurisdiction is not None:
            ward = self._provider.ward_for(jurisdiction)
            areas = self._provider.areas_at(longitude, latitude, on_date)
            road = self._provider.road_at(longitude, latitude, on_date)
            version = jurisdiction.version
        else:
            version = self._provider.version_active_on(on_date)

        return JurisdictionLookupResult(
            status=status,
            on_date=on_date,
            lat=latitude,
            lng=longitude,
            message=message,
            jurisdiction=self._jurisdiction_ref(jurisdiction) if jurisdiction else None,
            version=self._version_ref(version) if version else None,
            ward=self._ward_ref(ward) if ward else None,
            areas=[self._area_ref(a) for a in sorted(areas, key=lambda x: (x.code, x.id))],
            corridor=self._road_ref(road) if road else None,
            service_responsibility="NOT_EVALUATED",
        )

    def _jurisdiction_ref(self, jurisdiction: Jurisdiction) -> JurisdictionRef:
        return JurisdictionRef(
            id=jurisdiction.id,
            code=jurisdiction.code,
            name=jurisdiction.name,
            kind=jurisdiction.kind,
            version=self._version_ref(jurisdiction.version) if jurisdiction.version else None,
        )

    def _version_ref(self, version: JurisdictionVersion) -> JurisdictionVersionRef:
        return JurisdictionVersionRef(
            id=version.id,
            version_no=version.version_no,
            code=version.code,
            name=version.name,
            status=version.status,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
        )

    def _ward_ref(self, ward: Ward) -> WardRef:
        return WardRef(
            id=ward.id,
            ward_code=ward.ward_code,
            name=ward.name,
            locality=ward.locality,
            jurisdiction_id=ward.jurisdiction_id,
        )

    def _area_ref(self, area: Area) -> AreaRef:
        ward = area.ward
        return AreaRef(
            id=area.id,
            code=area.code,
            name=area.name,
            ward_code=ward.ward_code if ward else "",
            jurisdiction_id=ward.jurisdiction_id if ward else 0,
        )

    def _road_ref(self, road: Road) -> CorridorRef:
        return CorridorRef(
            id=road.id,
            code=road.code,
            name=road.name,
            road_class=road.road_class,
            jurisdiction_id=road.jurisdiction_id,
        )


def _windows_overlap(
    from_a: date,
    to_a: date | None,
    from_b: date,
    to_b: date | None,
) -> bool:
    """Closed-open interval overlap: [a, a') vs [b, b')."""
    end_a = to_a or _INFINITE
    end_b = to_b or _INFINITE
    return from_a < end_b and from_b < end_a


_INFINITE = date(9999, 12, 31)