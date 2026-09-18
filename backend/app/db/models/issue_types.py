"""Issue-type registry model — the citizen-facing taxonomy of reported issues."""
from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.base_mixins import TimestampMixin


class IssueType(Base, TimestampMixin):
    """A recognised civic issue a citizen can raise.

    Routing rules key on ``RoutingRule.issue_type_code``; this table is the
    authoritative catalogue of valid codes. Both the current citizen-facing
    taxonomy and historical legacy codes are seeded so old complaints stay
    routable. ``is_active`` only drives issue pickers — deactivation never
    deletes history or archived rules.
    """

    __tablename__ = "issue_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)