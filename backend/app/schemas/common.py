"""Pydantic schemas shared across endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiInfo(BaseModel):
    """Root endpoint payload."""

    name: str
    version: str
    docs: str


class ApiHealth(BaseModel):
    """Health endpoint payload."""

    status: str
    app_name: str
    app_version: str
    database_status: str
    seed_loaded: bool
    geometry_engine: str
    timestamp: datetime


class ApiErrorDetail(BaseModel):
    """One structured validation/problem detail."""

    loc: str | None = None
    message: str
    type: str | None = None


class ApiError(BaseModel):
    """Error envelope body."""

    code: str
    message: str
    details: list[ApiErrorDetail] = Field(default_factory=list)


class ApiErrorResponse(BaseModel):
    """Uniform error envelope for every failed request."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"error": {"code": "NOT_FOUND", "message": "", "details": []}}]})

    error: ApiError