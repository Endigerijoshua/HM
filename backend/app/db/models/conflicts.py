"""Responsibility conflict model.

Detects situations where geographic containment (Authority A) disagrees with
service-rule assignment (Authority B) — a core differentiator of this project.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.complaints import Complaint
    from app.db.models.reference import Authority


class ResponsibilityConflict(Base, TimestampMixin):
    """A detected mismatch between geographic and service responsibility."""

    __tablename__ = "responsibility_conflicts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    # OPEN | UNDER_REVIEW | RESOLVED | DISMISSED
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="OPEN")
    # GEO_VS_SERVICE | OVERLAP | NO_RULE
    conflict_type: Mapped[str] = mapped_column(String(30), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), index=True, nullable=True)
    geo_authority_id: Mapped[int] = mapped_column(ForeignKey("authorities.id"), index=True, nullable=False)
    service_authority_id: Mapped[int] = mapped_column(
        ForeignKey("authorities.id"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    complaint: Mapped[Complaint | None] = relationship(back_populates="conflicts")
    geo_authority: Mapped[Authority] = relationship(foreign_keys=[geo_authority_id])
    service_authority: Mapped[Authority] = relationship(foreign_keys=[service_authority_id])