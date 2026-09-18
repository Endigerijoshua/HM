"""Responsibility conflict model.

Detects situations where geographic containment (Authority A) disagrees with
service-rule assignment (Authority B) — a core differentiator of this project.
From P5 the same table also records department/service mismatches, temporal
rule conflicts and responsibility gaps produced by the deterministic
``ResponsibilityConflictService``.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.complaints import Complaint
    from app.db.models.reference import Authority, Department, Service


class ResponsibilityConflict(Base, TimestampMixin):
    """A detected mismatch between geographic and service responsibility."""

    __tablename__ = "responsibility_conflicts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    # OPEN | UNDER_REVIEW | RESOLVED | DISMISSED
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="OPEN")
    # GEO_VS_SERVICE | OVERLAP | NO_RULE | AUTHORITY_MISMATCH | DEPARTMENT_MISMATCH |
    # SERVICE_MISMATCH | TEMPORAL_RULE_CONFLICT | RESPONSIBILITY_GAP
    conflict_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # LOW | MEDIUM | HIGH (P5; nullable for legacy rows such as CF-1001)
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), index=True, nullable=True)
    issue_type_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    on_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    jurisdiction_code: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)

    # Expected responsibility (implied by the containing jurisdiction).
    geo_authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id"), index=True, nullable=True
    )
    expected_department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    expected_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id"), nullable=True
    )

    # Routed responsibility (assigned by the routing decision table).
    service_authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id"), index=True, nullable=True
    )
    routed_department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    routed_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id"), nullable=True
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    complaint: Mapped[Complaint | None] = relationship(back_populates="conflicts")
    geo_authority: Mapped[Authority | None] = relationship(foreign_keys=[geo_authority_id])
    service_authority: Mapped[Authority | None] = relationship(foreign_keys=[service_authority_id])
    expected_department: Mapped[Department | None] = relationship(
        foreign_keys=[expected_department_id]
    )
    expected_service: Mapped[Service | None] = relationship(foreign_keys=[expected_service_id])
    routed_department: Mapped[Department | None] = relationship(
        foreign_keys=[routed_department_id]
    )
    routed_service: Mapped[Service | None] = relationship(foreign_keys=[routed_service_id])