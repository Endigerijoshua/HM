"""Coordinate reference system helpers.

The API exchanges coordinates in WGS84 (EPSG:4326, always ``x=longitude``,
``y=latitude``). All metric computations (area, length, distance) are
performed in UTM zone 43N (EPSG:32643), which covers the Mysuru demo region.
"""
from __future__ import annotations

from functools import lru_cache

from pyproj import Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform

from app.core.errors import GeoValidationError

CRS_WGS84 = "EPSG:4326"
CRS_UTM_43N = "EPSG:32643"

# Mysuru sits inside UTM zone 43N; its X range is 300_000-700_000 m easting.
_UTM_43N = "EPSG:32643"


@lru_cache(maxsize=64)
def _transformer(from_crs: str, to_crs: str) -> Transformer:
    """Return a cached always_xy pyproj transformer for the CRS pair."""
    return Transformer.from_crs(from_crs, to_crs, always_xy=True)


def is_valid_coordinate(longitude: float, latitude: float) -> bool:
    """True when the point falls inside the WGS84 bounds."""
    return -180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0


def transform_xy(
    x: float,
    y: float,
    from_crs: str = CRS_WGS84,
    to_crs: str = _UTM_43N,
) -> tuple[float, float]:
    """Transform a single (x, y) pair between CRSs."""
    return _transformer(from_crs, to_crs).transform(x, y)


def transform_geometry(
    geometry: BaseGeometry,
    from_crs: str = CRS_WGS84,
    to_crs: str = _UTM_43N,
) -> BaseGeometry:
    """Reproject a shapely geometry, preserving its structure."""
    transformer = _transformer(from_crs, to_crs)
    return shapely_transform(lambda x, y: transformer.transform(x, y), geometry)


def project_to_metric(geometry: BaseGeometry) -> BaseGeometry:
    """Project a WGS84 geometry into UTM 43N for metric measurements."""
    if geometry.is_empty:
        raise GeoValidationError("Cannot project an empty geometry")
    return transform_geometry(geometry, CRS_WGS84, _UTM_43N)


def area_km2(geometry: BaseGeometry) -> float:
    """Planar area of a polygonal geometry in square kilometres (UTM 43N)."""
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise GeoValidationError(
            f"area_km2 requires a polygonal geometry, got {geometry.geom_type}"
        )
    return float(project_to_metric(geometry).area) / 1_000_000.0


def length_km(geometry: BaseGeometry) -> float:
    """Planar length of a linear geometry in kilometres (UTM 43N)."""
    if geometry.is_empty:
        return 0.0
    if geometry.geom_type not in {"LineString", "MultiLineString"}:
        raise GeoValidationError(
            f"length_km requires a linear geometry, got {geometry.geom_type}"
        )
    return float(project_to_metric(geometry).length) / 1000.0


def bounds(geometry: BaseGeometry) -> tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) in the geometry's own CRS."""
    if geometry.is_empty:
        raise GeoValidationError("Cannot compute bounds of an empty geometry")
    return geometry.bounds


def centroid_point(geometry: BaseGeometry) -> tuple[float, float]:
    """Return (longitude, latitude) of the centroid in WGS84."""
    centroid = geometry.centroid
    return float(centroid.x), float(centroid.y)