"""Shared column mixins for the ORM models."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` audit columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TemporalMixin:
    """Adds closed-open validity intervals ``[effective_from, effective_to)``.

    ``effective_to = NULL`` means "open ended". Rows are never mutated in
    place; a temporal change inserts a new row instead so historstorical
    records survive untouched.
    """

    effective_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)