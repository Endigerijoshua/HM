"""Application configuration loaded from environment variables.

Every option is read from env vars prefixed with ``TCIVIC_`` (e.g.
``TCIVIC_DATABASE_URL``) and may optionally be overridden through a local
``.env`` file. No secrets are hard-coded.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend service."""

    model_config = SettingsConfigDict(
        env_prefix="TCIVIC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Temporal Civic Jurisdiction Digital Twin"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"

    # --- Database -------------------------------------------------------
    database_url: str = "sqlite:///./temporal_civic.db"
    seed_on_startup: bool = True

    # --- GIS ------------------------------------------------------------
    # Geometry engine selector consumed by the GeometryProvider factory.
    # P0 wires "shapely" (SQLite + in-Python Shapely predicates). A future
    # PostGIS implementation ("postgis") will satisfy the same interface.
    geometry_engine: str = "shapely"

    # --- HTTP -----------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # --- Observability --------------------------------------------------
    log_level: str = "INFO"

    # --- Security (demo-grade) ------------------------------------------
    # Used from P1 onward for admin-only endpoints. Empty string = feature off.
    admin_token: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a cleaned list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()