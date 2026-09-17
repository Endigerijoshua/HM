"""Complaints and their event history."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.conflicts import ResponsibilityConflict
    from app.db.models.jurisdiction import Ward


class Complaint(Base, TimestampMixin):
    """A citizen report located at a single point."""

    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_ref: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    issue_type_code: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # OPEN | IN_PROGRESS | RESOLVED | CLOSED
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="OPEN")
    locality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="demo", nullable=False)

    ward: Mapped[Ward | None] = relationship()
    events: Mapped[list[ComplaintEvent]] = relationship(
        back_populates="complaint", order_by="ComplaintEvent.created_at"
    )
    conflicts: Mapped[list[ResponsibilityConflict]] = relationship(back_populates="complaint")


class ComplaintEvent(Base):
    """Append-only event stream for a complaint (status changes, reassignments…)."""

    __tablename__ = "complaint_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(60), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    complaint: Mapped[Complaint] = relationship(back_populates="events")