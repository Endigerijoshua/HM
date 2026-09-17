"""Demo GIS backend: geometry lives in SQLite, predicates run in Python.

Temporal selection is pushed to the database (SQLAlchemy query on the validity
interval); everything else (point-in-polygon, nearest corridor, sorting)
happens in Python with Shapely and is cached per jurisdiction row.

An STRtree spatial index is built lazily per date so repeated lookups against
the same temporal snapshot skip the linear scan.

A future ``PostGisProvider`` will keep the same public surface but delegate the
predicates to PostGIS SQL, so callers never notice the swap.
"""
from __future__ import annotations

from datetime import date

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree
from shapely.wkb import loads
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.jurisdiction import Area, Jurisdiction, JurisdictionVersion, Road, Ward
from app.gis.base import GeometryDecodeError, GeometryProvider, sort_jurisdictions

# Road-corridor snap distance in degrees (~55 m at Mysuru latitude). A point
# within this distance of a road's centreline is treated as "on the corridor".
ROAD_PROXIMITY_DEGREES = 0.0005

PointGeom = Point


class ShapelyGeometryProvider(GeometryProvider):
    """SQLite-hosted geometry with in-Python Shapely predicates (demo engine)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._geometry_cache: dict[int, BaseGeometry] = {}
        self._area_cache: dict[int, BaseGeometry] = {}
        self._road_cache: dict[int, BaseGeometry] = {}
        self._date_index: dict[date, tuple[list[Jurisdiction], STRtree]] = {}
        self._road_index: dict[date, tuple[list[Road], STRtree]] = {}
        self._area_index: dict[date, tuple[list[Area], STRtree]] = {}

    # --- internals ------------------------------------------------------

    def geometry_for(self, jurisdiction: Jurisdiction) -> BaseGeometry:
        geometry = self._geometry_cache.get(jurisdiction.id)
        if geometry is None:
            try:
                geometry = loads(bytes(jurisdiction.geometry_wkb))
            except Exception as exc:  # noqa: BLE001 - wrap decode failures
                raise GeometryDecodeError(
                    f"Could not decode WKB for jurisdiction {jurisdiction.code} ({jurisdiction.id})"
                ) from exc
            self._geometry_cache[jurisdiction.id] = geometry
        return geometry

    def to_geojson(self, geometry: BaseGeometry) -> dict:
        from shapely.geometry import mapping

        return mapping(geometry)

    def _area_geometry_for(self, area: Area) -> BaseGeometry:
        geometry = self._area_cache.get(area.id)
        if geometry is None:
            try:
                geometry = loads(bytes(area.geometry_wkb))
            except Exception as exc:  # noqa: BLE001 - wrap decode failures
                raise GeometryDecodeError(f"Could not decode WKB for area {area.code}") from exc
            self._area_cache[area.id] = geometry
        return geometry

    def _road_geometry_for(self, road: Road) -> BaseGeometry:
        geometry = self._road_cache.get(road.id)
        if geometry is None:
            try:
                geometry = loads(bytes(road.geometry_wkb))
            except Exception as exc:  # noqa: BLE001 - wrap decode failures
                raise GeometryDecodeError(f"Could not decode WKB for road {road.code}") from exc
            self._road_cache[road.id] = geometry
        return geometry

    def _active_index(self, on_date: date) -> tuple[list[Jurisdiction], STRtree]:
        cached = self._date_index.get(on_date)
        if cached is None:
            rows = self.jurisdictions_active_on(on_date)
            tree = STRtree([self.geometry_for(r) for r in rows])
            cached = (rows, tree)
            self._date_index[on_date] = cached
        return cached

    # --- public API -----------------------------------------------------

    def jurisdictions_active_on(self, on_date: date) -> list[Jurisdiction]:
        """Temporal filter only — spatial predicates are applied separately."""
        stmt = (
            select(Jurisdiction)
            .where(
                Jurisdiction.effective_from <= on_date,
                or_(Jurisdiction.effective_to.is_(None), on_date < Jurisdiction.effective_to),
            )
            .order_by(Jurisdiction.id)
        )
        return list(self._session.scalars(stmt))

    def jurisdiction_at(self, longitude: float, latitude: float, on_date: date) -> Jurisdiction | None:
        """Best jurisdiction containing the point on the date (kind-priority tie-break)."""
        matches = self.jurisdictions_containing(longitude, latitude, on_date)
        if not matches:
            return None
        return matches[0]

    def jurisdictions_containing(
        self, longitude: float, latitude: float, on_date: date
    ) -> list[Jurisdiction]:
        """Every active jurisdiction whose geometry contains the point, deterministically sorted.

        Uses the lazily-built STRtree to prune the candidates before the precise
        ``covers`` predicate. Overlapping/superimposed jurisdictions (ward +
        heritage overlay) are all returned; callers resolve extent ranking.
        """
        rows, tree = self._active_index(on_date)
        if not rows:
            return []
        point = PointGeom(longitude, latitude)
        candidates = [rows[i] for i in tree.query(point)]
        matches = [r for r in candidates if self.geometry_for(r).covers(point)]
        return sort_jurisdictions(matches)

    def ward_for(self, jurisdiction: Jurisdiction) -> Ward | None:
        if jurisdiction.kind != "WARD":
            return None
        return (
            self._session.query(Ward)
            .filter(Ward.jurisdiction_id == jurisdiction.id)
            .first()
        )

    def areas_active_on(self, on_date: date) -> list[Area]:
        stmt = (
            select(Area)
            .where(
                Area.effective_from <= on_date,
                or_(Area.effective_to.is_(None), on_date < Area.effective_to),
            )
            .order_by(Area.code)
        )
        return list(self._session.scalars(stmt))

    def area_at(self, longitude: float, latitude: float, on_date: date) -> Area | None:
        rows = self.areas_active_on(on_date)
        if not rows:
            return None
        point = PointGeom(longitude, latitude)
        for area in rows:
            if self._area_geometry_for(area).covers(point):
                return area
        return None

    def areas_at(self, longitude: float, latitude: float, on_date: date) -> list[Area]:
        rows = self.areas_active_on(on_date)
        if not rows:
            return []
        point = PointGeom(longitude, latitude)
        return [a for a in rows if self._area_geometry_for(a).covers(point)]

    def roads_active_on(self, on_date: date) -> list[Road]:
        stmt = (
            select(Road)
            .where(
                Road.effective_from <= on_date,
                or_(Road.effective_to.is_(None), on_date < Road.effective_to),
            )
            .order_by(Road.code)
        )
        return list(self._session.scalars(stmt))

    def road_at(self, longitude: float, latitude: float, on_date: date) -> Road | None:
        rows = self.roads_active_on(on_date)
        if not rows:
            return None
        point = PointGeom(longitude, latitude)
        for road in rows:
            geometry = self._road_geometry_for(road)
            if point.distance(geometry) <= ROAD_PROXIMITY_DEGREES:
                return road
        return None

    def version_active_on(self, on_date: date) -> JurisdictionVersion | None:
        stmt = (
            select(JurisdictionVersion)
            .where(
                JurisdictionVersion.effective_from <= on_date,
                or_(JurisdictionVersion.effective_to.is_(None), on_date < JurisdictionVersion.effective_to),
            )
            .order_by(JurisdictionVersion.version_no)
        )
        rows = list(self._session.scalars(stmt))
        return rows[0] if rows else None

    def all_jurisdictions(self) -> list[Jurisdiction]:
        """All stored jurisdiction rows, regardless of validity window."""
        return list(
            self._session.scalars(select(Jurisdiction).order_by(Jurisdiction.id))
        )