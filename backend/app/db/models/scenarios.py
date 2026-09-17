"""What-if scenarios, migration plans and migration items.

Simulation scenarios carry proposed geometry that is isolated from the live
``jurisdictions`` table — running a scenario must never mutate production data.
Applying it later creates migration plans whose items snapshot the responsibility
before/after so complaint history remains fully auditable.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.complaints import Complaint
    from app.db.models.jurisdiction import Jurisdiction
    from app.db.models.reference import Authority


class SimulationScenario(Base):
    """A proposed (what-if) boundary change that never touches live data."""

    __tablename__ = "simulation_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DRAFT | SIMULATED | APPLIED | DISCARDED
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="DRAFT")
    applies_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    affected_region_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    geometry_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    geometry_wkb: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    envelope_geojson: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_by: Mapped[str] = mapped_column(String(60), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plans: Mapped[list[MigrationPlan]] = relationship(back_populates="scenario")


class MigrationPlan(Base):
    """A preview/apply container for complaints affected by a scenario."""

    __tablename__ = "migration_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_scenarios.id"), index=True, nullable=False
    )
    # DRAFT | SIMULATED | APPLIED | DISCARDED
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="DRAFT")
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    affected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(60), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario: Mapped[SimulationScenario] = relationship(back_populates="plans")
    items: Mapped[list[MigrationItem]] = relationship(back_populates="plan")


class MigrationItem(Base):
    """Per-complaint responsibility migration record with before/after snapshots."""

    __tablename__ = "migration_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("migration_plans.id"), index=True, nullable=False)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True, nullable=False)
    current_authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id"), index=True, nullable=True
    )
    proposed_authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id"), index=True, nullable=True
    )
    current_jurisdiction_id: Mapped[int | None] = mapped_column(
        ForeignKey("jurisdictions.id"), index=True, nullable=True
    )
    proposed_jurisdiction_id: Mapped[int | None] = mapped_column(
        ForeignKey("jurisdictions.id"), index=True, nullable=True
    )
    # PENDING | APPLIED | SKIPPED | FAILED
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False, default="PENDING")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    plan: Mapped[MigrationPlan] = relationship(back_populates="items")
    complaint: Mapped[Complaint] = relationship()
    current_authority: Mapped[Authority | None] = relationship(foreign_keys=[current_authority_id])
    proposed_authority: Mapped[Authority | None] = relationship(foreign_keys=[proposed_authority_id])
    current_jurisdiction: Mapped[Jurisdiction | None] = relationship(
        foreign_keys=[current_jurisdiction_id]
    )
    proposed_jurisdiction: Mapped[Jurisdiction | None] = relationship(
        foreign_keys=[proposed_jurisdiction_id]
    )