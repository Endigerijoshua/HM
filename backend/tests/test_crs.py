"""CRS helpers and coordinate validation tests (P1)."""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from app.core.errors import GeoValidationError
from app.gis.crs import (
    CRS_UTM_43N,
    CRS_WGS84,
    area_km2,
    bounds,
    centroid_point,
    is_valid_coordinate,
    length_km,
    project_to_metric,
    transform_geometry,
    transform_xy,
)


def test_valid_coordinates_accepted() -> None:
    assert is_valid_coordinate(0.0, 0.0) is True
    assert is_valid_coordinate(76.64, 12.28) is True
    assert is_valid_coordinate(-180.0, -90.0) is True
    assert is_valid_coordinate(180.0, 90.0) is True


@pytest.mark.parametrize(
    "lng,lat",
    [(-180.1, 0.0), (180.1, 0.0), (0.0, -90.1), (0.0, 90.1), (200.0, 12.0), (76.0, 95.0)],
)
def test_invalid_coordinates_rejected(lng: float, lat: float) -> None:
    assert is_valid_coordinate(lng, lat) is False


def test_transform_xy_to_utm_and_back() -> None:
    x, y = 76.64, 12.28
    ew, ns = transform_xy(x, y, CRS_WGS84, CRS_UTM_43N)
    assert 200_000 < ew < 800_000
    assert 1_300_000 < ns < 1_500_000
    lng, lat = transform_xy(ew, ns, CRS_UTM_43N, CRS_WGS84)
    assert pytest.approx(lng, abs=1e-9) == x
    assert pytest.approx(lat, abs=1e-9) == y


def test_projection_geometry() -> None:
    polygon = Polygon([(76.56, 12.22), (76.72, 12.22), (76.72, 12.335), (76.56, 12.335)])
    projected = project_to_metric(polygon)
    assert projected.geom_type == "Polygon"
    assert projected.area > 1e8  # square metres (~2.1e8)


def test_area_km2_of_demo_bbox() -> None:
    polygon = Polygon([(76.56, 12.22), (76.72, 12.22), (76.72, 12.335), (76.56, 12.335)])
    km2 = area_km2(polygon)
    # ~213 km2 for the 0.16 x 0.115 degree demo bbox at Mysuru latitude
    assert 180 < km2 < 260
    assert km2 > 0


def test_area_km2_rejects_linear_geometry() -> None:
    from shapely.geometry import LineString

    with pytest.raises(GeoValidationError):
        area_km2(LineString([(76.56, 12.22), (76.72, 12.22)]))


def test_area_km2_empty_polygon_returns_zero() -> None:
    assert area_km2(Polygon()) == 0.0


def test_length_km_of_corridor() -> None:
    from shapely.geometry import LineString

    line = LineString([(76.56, 12.337), (76.72, 12.337)])
    km = length_km(line)
    assert 15 < km < 20


def test_bounds_and_centroid() -> None:
    polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    assert bounds(polygon) == (0.0, 0.0, 1.0, 1.0)
    cx, cy = centroid_point(polygon)
    assert (cx, cy) == pytest.approx((0.5, 0.5), abs=1e-9)


def test_transform_geometry_preserves_type() -> None:
    polygon = Polygon([(76.56, 12.22), (76.72, 12.22), (76.72, 12.335), (76.56, 12.335)])
    projected = transform_geometry(polygon, CRS_WGS84, CRS_UTM_43N)
    assert projected.geom_type == "Polygon"
    assert projected.bounds[0] > 0  # easting in UTM 43N is positive near Mysuru