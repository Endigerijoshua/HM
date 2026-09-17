"""Declarative base for all ORM models."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class shared by every SQLAlchemy model."""

    def __repr__(self) -> str:
        keys = list(self.__table__.columns.keys())[:4]
        parts = ", ".join(f"{k}={getattr(self, k)!r}" for k in keys)
        return f"<{self.__class__.__name__}({parts})>"