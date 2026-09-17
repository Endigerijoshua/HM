"""GIS provider abstraction + Shapely implementation tests."""
from __future__ import annotations

from datetime import date

import pytest
from shapely.geometry import Point

from app.core.errors import GeoValidationError
from app.gis.base import GeometryProvider, sort_jurisdictions
from app.gis.shapely_provider import ShapelyGeometryProvider


def test_point_in_ward_resolves_to_mcc(db) -> None:
    provider = ShapelyGeometryProvider(db)
    jurisdiction = provider.jurisdiction_at(76.64, 12.28, date(2024, 6, 1))
    assert jurisdiction is not None
    assert jurisdiction.kind == "WARD"
    assert jurisdiction.authority.code == "A-MCC"


def test_corridor_point_resolves_to_nhai(db) -> None:
    provider = ShapelyGeometryProvider(db)
    jurisdiction = provider.jurisdiction_at(76.66, 12.337, date(2024, 6, 1))
    assert jurisdiction is not None
    assert jurisdiction.kind == "SPECIAL_CORRIDOR"
    assert jurisdiction.authority.code == "A-NHAI"


def test_heritage_overlay_ranked_below_ward(db) -> None:
    """A point inside the heritage overlay that is also inside a ward yields the ward."""
    provider = ShapelyGeometryProvider(db)
    jurisdiction = provider.jurisdiction_at(76.635, 12.312, date(2024, 6, 1))
    assert jurisdiction is not None
    assert jurisdiction.kind == "WARD"


def test_date_outside_all_windows_returns_none(db) -> None:
    provider = ShapelyGeometryProvider(db)
    assert provider.jurisdiction_at(76.64, 12.28, date(2019, 6, 1)) is None


def test_active_jurisdiction_counts_per_version(db) -> None:
    provider = ShapelyGeometryProvider(db)
    assert len(provider.jurisdictions_active_on(date(2023, 6, 1))) == 10
    assert len(provider.jurisdictions_active_on(date(2024, 6, 1))) == 11


def test_geodata_roundtrip(db) -> None:
    provider = ShapelyGeometryProvider(db)
    jurisdictions = provider.jurisdictions_active_on(date(2024, 6, 1))
    for item in jurisdictions:
        geometry = provider.geometry_for(item)
        geojson = provider.to_geojson(geometry)
        assert geojson["type"] in {"Polygon", "MultiPolygon"}


def test_geojson_validation_accepts_valid_polygon() -> None:
    valid = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
    }
    geometry = GeometryProvider.validate_geojson_geometry(valid)
    assert geometry.is_valid


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "Point", "coordinates": [0.0, 0.0]},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]},
        "not-a-dict",
    ],
)
def test_geojson_validation_rejects_bad_payloads(payload) -> None:
    with pytest.raises(GeoValidationError):
        GeometryProvider.validate_geojson_geometry(payload)


def test_sort_jurisdictions_is_deterministic(db) -> None:
    """sort_jurisdictions orders by kind priority (WARD first) then code."""
    provider = ShapelyGeometryProvider(db)
    rows = provider.jurisdictions_active_on(date(2024, 6, 1))
    ordered = [row.code for row in sort_jurisdictions(rows)]
    assert ordered[:9] == [f"W-{index:02d}" for index in range(1, 10)]
    assert ordered[9] == "HER-01"  # heritage zone below wards
    assert ordered[10] == "NH-NEW"  # corridor last


def test_point_class_matches_provider_coordinates(db) -> None:
    """Provider honours (longitude, latitude) ordering like GeoJSON."""
    provider = ShapelyGeometryProvider(db)
    jurisdiction = provider.jurisdiction_at(76.64, 12.28, date(2024, 6, 1))
    point = Point(76.64, 12.28)
    assert provider.geometry_for(jurisdiction).covers(point)