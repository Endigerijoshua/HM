"""ORM models package.

Importing this package registers every model on ``Base.metadata`` (a required
side-effect before ``create_all`` runs).
"""
from app.db.base import Base
from app.db.models.audit import AuditLog
from app.db.models.base_mixins import TemporalMixin, TimestampMixin
from app.db.models.complaints import Complaint, ComplaintEvent
from app.db.models.conflicts import ResponsibilityConflict
from app.db.models.jurisdiction import (
    Area,
    Jurisdiction,
    JurisdictionChange,
    JurisdictionVersion,
    Road,
    Ward,
)
from app.db.models.reference import Authority, Department, Service
from app.db.models.routing import RoutingRule
from app.db.models.scenarios import MigrationItem, MigrationPlan, SimulationScenario

__all__ = [
    "Base",
    "Area",
    "AuditLog",
    "Authority",
    "Complaint",
    "ComplaintEvent",
    "Department",
    "Jurisdiction",
    "JurisdictionChange",
    "JurisdictionVersion",
    "MigrationItem",
    "MigrationPlan",
    "ResponsibilityConflict",
    "Road",
    "RoutingRule",
    "Service",
    "SimulationScenario",
    "TemporalMixin",
    "TimestampMixin",
    "Ward",
]