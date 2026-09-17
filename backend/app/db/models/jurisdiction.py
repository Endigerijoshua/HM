"""Temporal jurisdiction models.

Design principles
-----------------
* ``jurisdiction_versions`` group coherent, versioned snapshots of the boundary
  set (e.g. "Delimitation 2020", "Delimitation 2024").
* Individual ``jurisdictions`` carry closed-open validity intervals
  ``[effective_from, effective_to)`` so historical records stay queryable.
* Jurisdiction rows are never overwritten; a boundary change inserts a new row
  and a ``JurisdictionChange`` row records the transition.
* Geometry is stored twice: as GeoJSON text (API/UI friendly) and as WKB
  (Shapely/PostGIS ready).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.reference import Authority, Department, Service


class JurisdictionVersion(Base, TimestampMixin):
    """A coherent version of the entire boundary dataset."""

    __tablename__ = "jurisdiction_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_no: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # CURRENT | PROPOSED | SUPERSEDED | DRAFT
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="CURRENT")
    effective_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    created_by: Mapped[str] = mapped_column(String(60), default="system", nullable=False)

    jurisdictions: Mapped[list[Jurisdiction]] = relationship(back_populates="version")
    changes: Mapped[list[JurisdictionChange]] = relationship(back_populates="version")


class Jurisdiction(Base, TimestampMixin):
    """A single jurisdiction feature (ward, zone, heritage precinct, corridor…)."""

    __tablename__ = "jurisdictions"
    __table_args__ = (
        UniqueConstraint("code", "effective_from", name="uq_jurisdictions_code_effective_from"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # WARD | ZONE | AREA | HERITAGE_ZONE | SPECIAL_CORRIDOR
    kind: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    authority_id: Mapped[int] = mapped_column(ForeignKey("authorities.id"), index=True, nullable=False)
    jurisdiction_version_id: Mapped[int] = mapped_column(
        ForeignKey("jurisdiction_versions.id"), index=True, nullable=False
    )

    geometry_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    geometry_wkb: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    envelope_geojson: Mapped[str] = mapped_column(Text, nullable=False)

    parent_jurisdiction_id: Mapped[int | None] = mapped_column(
        ForeignKey("jurisdictions.id"), nullable=True
    )
    superseded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("jurisdictions.id"), nullable=True
    )

    effective_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    authority: Mapped[Authority] = relationship(back_populates="jurisdictions")
    version: Mapped[JurisdictionVersion] = relationship(back_populates="jurisdictions")

    parent_jurisdiction: Mapped[Jurisdiction | None] = relationship(
        "Jurisdiction", remote_side=[id], foreign_keys=[parent_jurisdiction_id]
    )
    superseded_by: Mapped[Jurisdiction | None] = relationship(
        "Jurisdiction", remote_side=[id], foreign_keys=[superseded_by_id]
    )

    ward: Mapped[Ward | None] = relationship(back_populates="jurisdiction", uselist=False)
    roads: Mapped[list[Road]] = relationship(back_populates="jurisdiction")

    changes_as_old: Mapped[list[JurisdictionChange]] = relationship(
        back_populates="from_jurisdiction", foreign_keys="JurisdictionChange.from_jurisdiction_id"
    )
    changes_as_new: Mapped[list[JurisdictionChange]] = relationship(
        back_populates="to_jurisdiction", foreign_keys="JurisdictionChange.to_jurisdiction_id"
    )


class JurisdictionChange(Base):
    """Append-only record of how a jurisdiction feature transitioned between versions."""

    __tablename__ = "jurisdiction_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    jurisdiction_version_id: Mapped[int] = mapped_column(
        ForeignKey("jurisdiction_versions.id"), index=True, nullable=False
    )
    from_jurisdiction_id: Mapped[int | None] = mapped_column(
        ForeignKey("jurisdictions.id"), index=True, nullable=True
    )
    to_jurisdiction_id: Mapped[int | None] = mapped_column(
        ForeignKey("jurisdictions.id"), index=True, nullable=True
    )
    # CREATED | MODIFIED | SUPERSEDED | SPLIT | MERGED | REMOVED
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped[JurisdictionVersion] = relationship(back_populates="changes")
    from_jurisdiction: Mapped[Jurisdiction | None] = relationship(
        foreign_keys=[from_jurisdiction_id], back_populates="changes_as_old"
    )
    to_jurisdiction: Mapped[Jurisdiction | None] = relationship(
        foreign_keys=[to_jurisdiction_id], back_populates="changes_as_new"
    )


class Ward(Base):
    """Administrative ward label attached to a ward-type jurisdiction."""

    __tablename__ = "wards"

    id: Mapped[int] = mapped_column(primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(
        ForeignKey("jurisdictions.id"), unique=True, index=True, nullable=False
    )
    ward_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    locality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="ward")
    areas: Mapped[list[Area]] = relationship(back_populates="ward")


class Area(Base):
    """A named locality that sits inside a ward."""

    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ward_id: Mapped[int] = mapped_column(ForeignKey("wards.id"), index=True, nullable=False)

    geometry_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    geometry_wkb: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    envelope_geojson: Mapped[str] = mapped_column(Text, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ward: Mapped[Ward] = relationship(back_populates="areas")


class Road(Base):
    """A road feature used for what-if impact analysis in later phases."""

    __tablename__ = "roads"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # NH | SH | CITY | INTERNAL
    road_class: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdictions.id"), index=True, nullable=False)
    jurisdiction_version_id: Mapped[int] = mapped_column(
        ForeignKey("jurisdiction_versions.id"), index=True, nullable=False
    )

    geometry_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    geometry_wkb: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    envelope_geojson: Mapped[str] = mapped_column(Text, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="roads")
    version: Mapped[JurisdictionVersion] = relationship()