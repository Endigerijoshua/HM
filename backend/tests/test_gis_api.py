"""GIS API endpoint tests (P1)."""
from __future__ import annotations

from datetime import date

import pytest


def test_list_jurisdictions_all(client) -> None:
    response = client.get("/api/v1/gis/jurisdictions")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 21
    codes = [j["code"] for j in body["jurisdictions"]]
    assert "W-01" in codes
    assert "HER-01" in codes
    assert "NH-NEW" in codes


def test_list_jurisdictions_temporal_filter(client) -> None:
    response = client.get("/api/v1/gis/jurisdictions", params={"date": "2023-06-01"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 10  # 9 wards + NH-OLD
    assert body["on_date"] == "2023-06-01"

    response = client.get("/api/v1/gis/jurisdictions", params={"date": "2026-07-01"})
    assert response.status_code == 200
    # V2 still current at that date; V3 is PROPOSED and holds no live rows.
    assert response.json()["count"] == 11


def test_list_jurisdictions_kind_and_version_filters(client) -> None:
    kind = client.get("/api/v1/gis/jurisdictions", params={"kind": "WARD"}).json()
    assert kind["count"] == 18  # 9 W-01..W-09 x 2 versions

    v2 = client.get("/api/v1/gis/jurisdictions", params={"version_id": 2}).json()
    assert v2["count"] == 11  # 9 wards + NH-NEW + HER-01


def test_list_jurisdictions_include_geometry(client) -> None:
    response = client.get(
        "/api/v1/gis/jurisdictions",
        params={"include_geometry": "true", "kind": "WARD"},
    )
    assert response.status_code == 200
    for item in response.json()["jurisdictions"]:
        assert item["geometry_geojson"]["type"] in {"Polygon", "MultiPolygon"}


def test_get_jurisdiction_detail(client) -> None:
    listing = client.get("/api/v1/gis/jurisdictions").json()["jurisdictions"]
    first = listing[0]
    response = client.get(f"/api/v1/gis/jurisdictions/{first['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == first["code"]
    assert body["geometry_geojson"]["type"] == "Polygon"


def test_get_jurisdiction_404(client) -> None:
    response = client.get("/api/v1/gis/jurisdictions/99999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_jurisdiction_versions_history(client) -> None:
    listing = client.get("/api/v1/gis/jurisdictions", params={"kind": "WARD"}).json()
    codes = {j["code"] for j in listing["jurisdictions"]}
    assert "W-01" in codes
    w01 = next(j for j in listing["jurisdictions"] if j["code"] == "W-01")
    response = client.get(f"/api/v1/gis/jurisdictions/{w01['id']}/versions")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "W-01"
    assert body["count"] == 2
    assert [e["version"]["code"] for e in body["entries"]] == ["DELIM-2020", "DELIM-2024"]


def test_lookup_matched(client) -> None:
    response = client.post(
        "/api/v1/gis/lookup",
        json={"lat": 12.28, "lng": 76.64, "on_date": "2024-06-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "MATCHED"
    assert body["jurisdiction"]["kind"] == "WARD"
    assert body["version"]["code"] == "DELIM-2024"
    assert body["service_responsibility"] == "NOT_EVALUATED"


def test_lookup_historical_different_result(client) -> None:
    old = client.post(
        "/api/v1/gis/lookup",
        json={"lat": 12.28, "lng": 76.64, "on_date": "2023-06-01"},
    ).json()
    new = client.post(
        "/api/v1/gis/lookup",
        json={"lat": 12.28, "lng": 76.64, "on_date": "2024-06-01"},
    ).json()
    assert old["status"] == "MATCHED"
    assert new["status"] == "MATCHED"
    assert old["version"]["code"] == "DELIM-2020"
    assert new["version"]["code"] == "DELIM-2024"
    assert old["jurisdiction"]["id"] != new["jurisdiction"]["id"]


def test_lookup_no_jurisdiction(client) -> None:
    response = client.post(
        "/api/v1/gis/lookup",
        json={"lat": 12.28, "lng": 76.64, "on_date": "2024-01-01"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "NO_JURISDICTION"


def test_lookup_invalid_coordinates_422(client) -> None:
    response = client.post(
        "/api/v1/gis/lookup",
        json={"lat": 91.0, "lng": 76.64, "on_date": "2024-06-01"},
    )
    assert response.status_code == 422


def test_lookup_corridor(client) -> None:
    response = client.post(
        "/api/v1/gis/lookup",
        json={"lat": 12.337, "lng": 76.66, "on_date": "2024-06-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "MATCHED"
    assert body["jurisdiction"]["kind"] == "SPECIAL_CORRIDOR"
    assert body["corridor"]["code"] == "ROAD-NH"


def test_validate_geometry_valid_polygon(client) -> None:
    response = client.post(
        "/api/v1/gis/validate-geometry",
        json={
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_validate_geometry_invalid_with_repair(client) -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
    }
    response = client.post(
        "/api/v1/gis/validate-geometry",
        json={"geometry": bowtie, "repair": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["repair"] is not None
    assert body["repair"]["required"] is True


def test_repair_geometry(client) -> None:
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
    }
    response = client.post("/api/v1/gis/repair-geometry", json={"geometry": bowtie})
    assert response.status_code == 200
    body = response.json()
    assert body["required"] is True
    assert body["was_changed"] is True
    assert body["geometry"] is not None


def test_describe_geometry(client) -> None:
    response = client.post(
        "/api/v1/gis/describe",
        json={
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[76.56, 12.22], [76.72, 12.22], [76.72, 12.335], [76.56, 12.335], [76.56, 12.22]]
                ],
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["geometry_type"] == "Polygon"
    assert body["area_km2"] is not None
    assert body["bounds"]["minx"] == pytest.approx(76.56)
    assert body["centroid"]["lat"] == pytest.approx((12.22 + 12.335) / 2, abs=0.01)


def test_operations_intersection(client) -> None:
    response = client.post(
        "/api/v1/gis/operations",
        json={
            "operation": "intersection",
            "a": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
            },
            "b": {
                "type": "Polygon",
                "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]],
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["operation"] == "intersection"
    assert body["result_type"] == "Polygon"
    assert body["result"] is not None


def test_operations_predicate(client) -> None:
    response = client.post(
        "/api/v1/gis/operations",
        json={
            "operation": "intersects",
            "a": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
            },
            "b": {
                "type": "Polygon",
                "coordinates": [[[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]],
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["value"] is True


def test_transform_endpoint(client) -> None:
    response = client.post(
        "/api/v1/gis/transform",
        json={
            "geometry": {
                "type": "Point",
                "coordinates": [76.64, 12.28],
            },
            "from_crs": "EPSG:4326",
            "to_crs": "EPSG:32643",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["crs"] == "EPSG:32643"
    assert len(body["geometry"]["coordinates"]) == 2


def test_wards_endpoint(client) -> None:
    response = client.get("/api/v1/gis/wards")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 9
    codes = {w["ward_code"] for w in body["wards"]}
    assert codes == {f"W-{i:02d}" for i in range(1, 10)}


def test_areas_endpoint(client) -> None:
    response = client.get("/api/v1/gis/areas")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert {a["code"] for a in body["areas"]} == {"AREA-VVM", "AREA-UDAY", "AREA-GOK"}


def test_roads_endpoint(client) -> None:
    response = client.get("/api/v1/gis/roads")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 4
    assert "ROAD-NH" in {r["code"] for r in body["roads"]}