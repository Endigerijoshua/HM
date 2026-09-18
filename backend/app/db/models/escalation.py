"""Escalation-step model — ordered escalation ladder attached to a routing rule."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.reference import Authority, Department, Service
    from app.db.models.routing import RoutingRule


class EscalationStep(Base, TimestampMixin):
    """One step in a rule's escalation ladder; step 1 is the first responder.

    Steps are displayed to the citizen as the path their issue follows when the
    first responder cannot close it (e.g. a state-highway stretch escalates a
    pothole from MCC to PWD).
    """

    __tablename__ = "escalation_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    routing_rule_id: Mapped[int] = mapped_column(
        ForeignKey("routing_rules.id"), index=True, nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    authority_id: Mapped[int] = mapped_column(ForeignKey("authorities.id"), index=True, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True, nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule: Mapped[RoutingRule] = relationship(back_populates="escalation_steps")
    authority: Mapped[Authority] = relationship()
    department: Mapped[Department] = relationship()
    service: Mapped[Service] = relationship()