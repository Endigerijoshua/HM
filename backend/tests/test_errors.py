"""Structured error handling tests."""
from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import register_exception_handlers


def test_unknown_path_returns_error_envelope(client) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"]


def test_method_not_allowed_returns_error_envelope(client) -> None:
    response = client.post("/api/v1/health")
    assert response.status_code == 405
    body = response.json()
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_request_validation_error_envelope() -> None:
    class Payload(BaseModel):
        value: int

    router = APIRouter()

    @router.post("/echo")
    def echo(payload: Payload) -> dict:
        return {"value": payload.value}

    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(router)

    response = TestClient(test_app).post("/echo", json={"value": "not-an-int"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"][0]["loc"]  # at least one structured detail