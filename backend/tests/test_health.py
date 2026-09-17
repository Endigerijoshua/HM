"""Health and metadata endpoint tests."""


def test_health_returns_ok(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database_status"] == "ok"
    assert body["seed_loaded"] is True
    assert body["geometry_engine"] == "shapely"
    assert body["app_version"]


def test_root_metadata(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"]
    assert body["version"]
    assert body["docs"] == "/docs"