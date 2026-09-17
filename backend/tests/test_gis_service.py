"""GisService: validation, repair, describe, spatial operations tests (P1)."""
from __future__ import annotations

import pytest
from shapely.geometry import shape

from app.core.errors import GeoValidationError
from app.gis.ops import GisService


def _service(db) -> GisService:
    from app.gis.shapely_provider import ShapelyGeometryProvider

    return GisService(ShapelyGeometryProvider(db))


def _square(minx, miny, maxx, maxy) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]
        ],
    }


def test_validate_accepts_valid_polygon(db) -> None:
    result = _service(db).validate(_square(0, 0, 1, 1))
    assert result.valid is True
    assert result.geometry_type == "Polygon"
    assert result.reason is None


@pytest.mark.parametrize(
    "geometry_type,expected",
    [
        ("Point", "Point"),
        ("MultiPoint", "MultiPoint"),
        ("LineString", "LineString"),
        ("MultiLineString", "MultiLineString"),
        ("Polygon", "Polygon"),
        ("MultiPolygon", "MultiPolygon"),
    ],
)
def test_validate_supports_geometry_types(db, geometry_type, expected) -> None:
    data = _geojson_for(geometry_type)
    result = _service(db).validate(data)
    assert result.valid is True
    assert result.geometry_type == expected


def _geojson_for(gtype: str) -> dict:
    if gtype == "Point":
        return {"type": "Point", "coordinates": [0.0, 0.0]}
    if gtype == "MultiPoint":
        return {"type": "MultiPoint", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}
    if gtype == "LineString":
        return {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}
    if gtype == "MultiLineString":
        return {
            "type": "MultiLineString",
            "coordinates": [[[0, 0], [1, 1]], [[2, 2], [3, 3]]],
        }
    if gtype == "Polygon":
        return _square(0, 0, 1, 1)
    return {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
        ],
    }


def test_validate_rejects_unparseable(db) -> None:
    result = _service(db).validate({"type": "Polygon", "coordinates": "nope"})
    assert result.valid is False
    assert result.reason


def test_validate_rejects_unsupported_type(db) -> None:
    result = _service(db).validate({"type": "GeometryCollection", "geometries": []})
    assert result.valid is False


def test_validate_rejects_empty_geometry(db) -> None:
    result = _service(db).validate({"type": "Polygon", "coordinates": []})
    assert result.valid is False


def test_validate_rejects_invalid_bowtie(db) -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
    }
    result = _service(db).validate(bowtie)
    assert result.valid is False
    assert result.reason and "Self-intersection" in result.reason


def test_validate_with_repair_reports_repair(db) -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
    }
    result = _service(db).validate(bowtie, repair=True)
    assert result.valid is False
    assert result.repair is not None
    assert result.repair.required is True
    assert result.repair.was_changed is True
    assert result.repair.report


def test_repair_valid_geometry_is_noop(db) -> None:
    result = _service(db).repair(_square(0, 0, 1, 1))
    assert result.required is False
    assert result.was_changed is False


def test_repair_invalid_bowtie_reports_change(db) -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
    }
    result = _service(db).repair(bowtie)
    assert result.required is True
    assert result.was_changed is True
    assert len(result.report) >= 2
    assert shape(result.geometry) is not None


def test_describe_polygon(db) -> None:
    result = _service(db).describe(_square(0, 0, 1, 1))
    assert result.geometry_type == "Polygon"
    assert result.parts == 1
    assert result.area_km2 is not None and result.area_km2 > 0
    assert result.bounds is not None
    assert result.centroid is not None
    assert result.bounds.minx == 0.0
    assert result.centroid["lon"] == pytest.approx(0.5, abs=1e-9)


def test_describe_linestring_reports_length(db) -> None:
    data = {"type": "LineString", "coordinates": [[76.56, 12.337], [76.72, 12.337]]}
    result = _service(db).describe(data)
    assert result.geometry_type == "LineString"
    assert result.length_km is not None and result.length_km > 15
    assert result.area_km2 is None


def test_operate_predicates(db) -> None:
    service = _service(db)
    a = _square(0, 0, 2, 2)
    b = _square(1, 1, 3, 3)
    assert service.operate("intersects", a, b).value is True
    assert service.operate("contains", a, b).value is False
    assert service.operate("within", b, a).value is False


def test_operate_intersection(db) -> None:
    a = _square(0, 0, 2, 2)
    b = _square(1, 1, 3, 3)
    result = _service(db).operate("intersection", a, b)
    assert result.result is not None
    assert result.result_type == "Polygon"
    assert shape(result.result).area == pytest.approx(1.0)


def test_operate_difference(db) -> None:
    a = _square(0, 0, 2, 2)
    b = _square(1, 1, 3, 3)
    result = _service(db).operate("difference", a, b)
    assert result.result is not None
    assert result.result_type == "Polygon"


def test_operate_union_area(db) -> None:
    a = _square(0, 0, 2, 2)
    b = _square(1, 1, 3, 3)
    result = _service(db).operate("union", a, b)
    assert result.result is not None
    # 4 + 4 - 1 overlap = 7
    assert shape(result.result).area == pytest.approx(7.0)


def test_operate_unknown_raises(db) -> None:
    with pytest.raises(GeoValidationError):
        _service(db).operate("blend", _square(0, 0, 1, 1), _square(0, 0, 1, 1))


def test_point_in_polygon(db) -> None:
    service = _service(db)
    assert service.point_in_polygon(0.5, 0.5, _square(0, 0, 1, 1)) is True
    assert service.point_in_polygon(5.0, 5.0, _square(0, 0, 1, 1)) is False


def test_transform_wgs84_to_utm(db) -> None:
    result = _service(db).transform(_square(76.56, 12.22, 76.6, 12.28), "EPSG:4326", "EPSG:32643")
    assert result.crs == "EPSG:32643"
    assert result.geometry["type"] == "Polygon"