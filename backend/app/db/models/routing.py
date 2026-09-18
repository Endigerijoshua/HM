"""Routing rule model — the decision table behind the future civic routing engine."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.escalation import EscalationStep
    from app.db.models.jurisdiction import Jurisdiction
    from app.db.models.reference import Authority, Department, Service


class RoutingRule(Base, TimestampMixin):
    """Map an issue type to the responsible authority/department/service.

    Rules are temporal (``[effective_from, effective_to)``) and may be scoped to
    the whole authority or to a specific jurisdiction. Lower ``priority`` wins;
    ties are broken deterministically by ``id``.
    """

    __tablename__ = "routing_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    # Demo uses service codes as issue-type codes (1:1). A dedicated issue-type
    # registry can be introduced later without altering this column.
    issue_type_code: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    authority_id: Mapped[int] = mapped_column(ForeignKey("authorities.id"), index=True, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True, nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True, nullable=False)

    # AUTHORITY_WIDE | JURISDICTION
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="AUTHORITY_WIDE")
    jurisdiction_id: Mapped[int | None] = mapped_column(
        ForeignKey("jurisdictions.id"), index=True, nullable=True
    )
    match_geography: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    effective_from: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    authority: Mapped[Authority] = relationship()
    department: Mapped[Department] = relationship()
    service: Mapped[Service] = relationship(back_populates="rules")
    jurisdiction: Mapped[Jurisdiction | None] = relationship()
    escalation_steps: Mapped[list[EscalationStep]] = relationship(
        back_populates="rule", order_by="EscalationStep.step_number"
    )