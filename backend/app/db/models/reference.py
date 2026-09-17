"""Reference/registry models: authorities, departments, services."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.jurisdiction import Jurisdiction
    from app.db.models.routing import RoutingRule


class Authority(Base, TimestampMixin):
    """An organization holding civic responsibility (e.g. MCC, MUDA, PWD, CESC, NHAI)."""

    __tablename__ = "authorities"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    authority_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="MUNICIPAL | PLANNING | STATE | UTILITY | NATIONAL"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    departments: Mapped[list[Department]] = relationship(back_populates="authority")
    jurisdictions: Mapped[list[Jurisdiction]] = relationship(back_populates="authority")


class Department(Base, TimestampMixin):
    """A department owned by an authority."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    authority_id: Mapped[int] = mapped_column(
        ForeignKey("authorities.id"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    authority: Mapped[Authority] = relationship(back_populates="departments")
    services: Mapped[list[Service]] = relationship(back_populates="department")


class Service(Base, TimestampMixin):
    """A civic service a citizen can raise an issue against."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general", nullable=False)
    sla_days: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    department: Mapped[Department] = relationship(back_populates="services")
    rules: Mapped[list[RoutingRule]] = relationship(back_populates="service")