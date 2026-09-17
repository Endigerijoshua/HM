"""GIS service: geometry validation, controlled repair, and spatial operations.

Thin, provider-driven service used by the GIS API router. Every return value is
a structured Pydantic model so callers can render results without shapely
knowledge. CRS/metric conversions go through :mod:`app.gis.crs`.

Validation policy: input geometry is parsed as a Shapely geometry in WGS84 and
checked for emptiness/CRS/type validity. If it is topologically invalid the
service reports the reason (never blindly fixes). Repair is an explicit,
opt-in step that returns a report describing what was done.
"""
from __future__ import annotations

from shapely.geometry import GeometryCollection, Point, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity, make_valid

from app.core.errors import GeoValidationError
from app.gis.base import GeometryProvider
from app.gis.crs import area_km2, bounds, centroid_point, length_km, transform_geometry
from app.schemas.gis import (
    BoundsRef,
    GeometryDescribeResult,
    GeometryRepairResult,
    GeometryValidationResult,
    SpatialOperationResult,
    TransformResult,
)

# Geometry types the GIS service understands and validates.
SUPPORTED_GEOMETRY_TYPES = {
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
}


class GisService:
    """Coordinates geometry validation, repair, describe and spatial algebra."""

    def __init__(self, provider: GeometryProvider) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # parsing helpers
    # ------------------------------------------------------------------

    def parse(self, data: dict, *, supported: set[str] | None = None) -> BaseGeometry:
        """Parse a GeoJSON mapping into a shapely geometry without mutating it.

        Raises ``GeoValidationError`` for malformed or unsupported input.
        """
        if not isinstance(data, dict):
            raise GeoValidationError("GeoJSON geometry must be a JSON object")
        allowed = supported or SUPPORTED_GEOMETRY_TYPES
        try:
            geometry = shape(data)
        except Exception as exc:  # noqa: BLE001 - normalize shapely failures
            raise GeoValidationError(f"Unparseable GeoJSON geometry: {exc}") from exc
        if geometry.is_empty:
            raise GeoValidationError("Geometry must not be empty")
        if geometry.geom_type not in allowed:
            raise GeoValidationError(
                f"Unsupported geometry type {geometry.geom_type!r}; expected one of {sorted(allowed)}"
            )
        return geometry

    def to_geojson(self, geometry: BaseGeometry) -> dict:
        return self._provider.to_geojson(geometry)

    # ------------------------------------------------------------------
    # validation & repair
    # ------------------------------------------------------------------

    def validate(self, data: dict, *, repair: bool = False) -> GeometryValidationResult:
        """Validate a GeoJSON geometry; optionally attach a repair result."""
        try:
            geometry = self.parse(data)
        except GeoValidationError as exc:
            return GeometryValidationResult(valid=False, reason=exc.message)
        if geometry.is_valid:
            return GeometryValidationResult(valid=True, geometry_type=geometry.geom_type)
        reason = explain_validity(geometry)
        result = GeometryValidationResult(valid=False, geometry_type=geometry.geom_type, reason=reason)
        if repair:
            result.repair = self._repair(data, geometry)
        return result

    def repair(self, data: dict) -> GeometryRepairResult:
        """Repair an invalid geometry and report exactly what changed."""
        try:
            geometry = self.parse(data)
        except GeoValidationError as exc:
            return GeometryRepairResult(
                required=False, was_changed=False, report=[exc.message]
            )
        return self._repair(data, geometry)

    def _repair(self, original_data: dict, geometry: BaseGeometry) -> GeometryRepairResult:
        if geometry.is_valid:
            return GeometryRepairResult(
                required=False,
                was_changed=False,
                geometry_type=geometry.geom_type,
                report=["Geometry is already valid — no repair needed"],
                geometry=original_data,
            )
        repaired = make_valid(geometry)
        changed = not repaired.equals(geometry)
        report = [explain_validity(geometry), f"Repaired as {repaired.geom_type}"]
        return GeometryRepairResult(
            required=True,
            was_changed=changed,
            geometry_type=repaired.geom_type,
            report=report,
            geometry=mapping(repaired) if not repaired.is_empty else None,
        )

    # ------------------------------------------------------------------
    # describe
    # ------------------------------------------------------------------

    def describe(self, data: dict) -> GeometryDescribeResult:
        """Analyse a geometry: type, area, bounds, centroid, components."""
        geometry = self.parse(data)
        if isinstance(geometry, GeometryCollection):
            parts = max(len(geometry.geoms), 1)
        else:
            parts = 1

        minx, miny, maxx, maxy = bounds(geometry) if not geometry.is_empty else (0.0, 0.0, 0.0, 0.0)
        c_lon, c_lat = centroid_point(geometry) if not geometry.is_empty else (None, None)

        area = None
        length = None
        if geometry.geom_type in {"Polygon", "MultiPolygon"}:
            area = round(area_km2(geometry), 6)
        elif geometry.geom_type in {"LineString", "MultiLineString"}:
            length = round(length_km(geometry), 6)

        return GeometryDescribeResult(
            geometry_type=geometry.geom_type,
            is_valid=geometry.is_valid,
            is_empty=geometry.is_empty,
            parts=parts,
            area_km2=area,
            length_km=length,
            bounds=BoundsRef(minx=minx, miny=miny, maxx=maxx, maxy=maxy),
            centroid={"lon": c_lon, "lat": c_lat} if c_lon is not None else None,
        )

    # ------------------------------------------------------------------
    # spatial algebra
    # ------------------------------------------------------------------

    def operate(
        self,
        operation: str,
        a: dict,
        b: dict,
    ) -> SpatialOperationResult:
        """Run a spatial predicate or set operation between two GeoJSON geometries."""
        ga = self.parse(a)
        gb = self.parse(b)

        if operation in {"intersects", "contains", "within"}:
            if operation == "intersects":
                value = ga.intersects(gb)
            elif operation == "contains":
                value = ga.contains(gb)
            else:
                value = ga.within(gb)
            return SpatialOperationResult(operation=operation, value=bool(value))

        if operation == "intersection":
            result = ga.intersection(gb)
        elif operation == "difference":
            result = ga.difference(gb)
        elif operation == "union":
            result = ga.union(gb)
        else:
            raise GeoValidationError(f"Unsupported spatial operation {operation!r}")

        warnings = []
        if result.is_empty:
            warnings.append("Result geometry is empty")
        return SpatialOperationResult(
            operation=operation,
            result=mapping(result) if not result.is_empty else None,
            result_type=result.geom_type if not result.is_empty else None,
            warnings=warnings,
        )

    def point_in_polygon(self, longitude: float, latitude: float, data: dict) -> bool:
        """True if the WGS84 point falls inside the given polygonal geometry."""
        geometry = self.parse(
            data, supported={"Polygon", "MultiPolygon"}
        )
        return geometry.covers(Point(longitude, latitude))

    def transform(self, data: dict, from_crs: str, to_crs: str) -> TransformResult:
        """Reproject a GeoJSON geometry between CRSs."""
        geometry = self.parse(data)
        projected = transform_geometry(geometry, from_crs, to_crs)
        return TransformResult(geometry=mapping(projected), crs=to_crs)

    def measure(self, data: dict) -> dict:
        """Return metric measurements (area/length/bounds) for a geometry."""
        geometry = self.parse(data)
        result: dict = {"geometry_type": geometry.geom_type, "crs": "EPSG:32643 (metric)"}
        if geometry.geom_type in {"Polygon", "MultiPolygon"}:
            result["area_km2"] = round(area_km2(geometry), 6)
        if geometry.geom_type in {"LineString", "MultiLineString"}:
            result["length_km"] = round(length_km(geometry), 6)
        result["bounds"] = list(bounds(geometry)) if not geometry.is_empty else []
        return result