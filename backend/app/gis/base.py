"""GIS storage abstraction.

The routing/business layers depend ONLY on this interface. P0 ships the
SQLite + in-Python Shapely implementation; a future PostGIS implementation
will satisfy the same interface by delegating to ``ST_*`` SQL — no business
logic changes required.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from shapely.geometry import Polygon, shape
from shapely.geometry.base import BaseGeometry

from app.core.errors import AppError, GeoValidationError
from app.db.models.jurisdiction import Area, Jurisdiction, JurisdictionVersion, Road, Ward


class GeometryDecodeError(AppError):
    """Stored geometry bytes could not be decoded by the provider."""

    status_code = 400
    code = "GEOMETRY_DECODE_ERROR"

# Deterministic disambiguation when a point falls inside several active
# jurisdictions of different kinds (e.g. ward vs heritage overlay).
KIND_RANK: dict[str, int] = {
    "WARD": 1,
    "AREA": 2,
    "HERITAGE_ZONE": 3,
    "ZONE": 4,
    "SPECIAL_CORRIDOR": 5,
}


def sort_jurisdictions(rows: list[Jurisdiction]) -> list[Jurisdiction]:
    """Order jurisdictions deterministically by kind then code."""
    return sorted(rows, key=lambda r: (KIND_RANK.get(r.kind, 99), r.code, r.id))


def sort_for_display(rows: list[Jurisdiction]) -> list[Jurisdiction]:
    """Deterministic display order: WARD < AREA < heritage < ZONE < corridor.

    Provided as a named convenience over :func:`sort_jurisdictions` for callers
    that want the intent spelled out.
    """
    return sort_jurisdictions(rows)


class GeometryProvider(ABC):
    """Spatial query interface implemented by GIS backends."""

    @abstractmethod
    def jurisdiction_at(self, longitude: float, latitude: float, on_date: date) -> Jurisdiction | None:
        """Return the deterministic best jurisdiction containing the point on a date."""

    @abstractmethod
    def jurisdictions_active_on(self, on_date: date) -> list[Jurisdiction]:
        """All jurisdictions temporally active on the given date."""

    @abstractmethod
    def geometry_for(self, jurisdiction: Jurisdiction) -> BaseGeometry:
        """Decode a jurisdiction's stored geometry into a shapely geometry."""

    @abstractmethod
    def to_geojson(self, geometry: BaseGeometry) -> dict:
        """Convert a shapely geometry to a GeoJSON geometry mapping."""

    @abstractmethod
    def ward_for(self, jurisdiction: Jurisdiction) -> Ward | None:
        """Return the ward label attached to a ward-kind jurisdiction, if any."""

    @abstractmethod
    def areas_active_on(self, on_date: date) -> list[Area]:
        """All areas temporally active on the given date."""

    @abstractmethod
    def area_at(self, longitude: float, latitude: float, on_date: date) -> Area | None:
        """Return the area containing the point on the date, if any."""

    @abstractmethod
    def areas_at(self, longitude: float, latitude: float, on_date: date) -> list[Area]:
        """Return every active area containing the point on the date."""

    @abstractmethod
    def roads_active_on(self, on_date: date) -> list[Road]:
        """All road features temporally active on the given date."""

    @abstractmethod
    def road_at(self, longitude: float, latitude: float, on_date: date) -> Road | None:
        """Return the road corridor containing the point on the date, if any."""

    @abstractmethod
    def version_active_on(self, on_date: date) -> JurisdictionVersion | None:
        """Return the boundary version in force on the given date, if any."""

    @abstractmethod
    def all_jurisdictions(self) -> list[Jurisdiction]:
        """Return every stored jurisdiction row regardless of temporal window."""

    @staticmethod
    def validate_geojson_geometry(data: dict) -> Polygon:
        """Validate an incoming GeoJSON Polygon/MultiPolygon description."""
        if not isinstance(data, dict):
            raise GeoValidationError("GeoJSON geometry must be a JSON object")
        try:
            geometry = shape(data)
        except Exception as exc:  # noqa: BLE001 - normalize shapely failures
            raise GeoValidationError(f"Unparseable GeoJSON geometry: {exc}") from exc
        if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise GeoValidationError(f"Expected Polygon/MultiPolygon, got {geometry.geom_type}")
        if geometry.is_empty:
            raise GeoValidationError("Geometry must not be empty")
        if not geometry.is_valid:
            raise GeoValidationError("Geometry is invalid (self-intersection or degenerate ring)")
        return geometry


class GeometryNotAvailableError(RuntimeError):
    """Raised when the configured geometry engine is not wired up."""