"""Error and id helpers for the core layer."""
from app.core.errors import (
    AppError,
    ForbiddenError,
    GeoValidationError,
    NotFoundError,
    ResponsibilityUnresolvedError,
    register_exception_handlers,
)
from app.core.ids import (
    complaint_public_ref,
    conflict_reference,
    migration_plan_reference,
    new_reference,
    route_reference,
    scenario_reference,
)

__all__ = [
    "AppError",
    "ForbiddenError",
    "GeoValidationError",
    "NotFoundError",
    "ResponsibilityUnresolvedError",
    "register_exception_handlers",
    "complaint_public_ref",
    "conflict_reference",
    "migration_plan_reference",
    "new_reference",
    "route_reference",
    "scenario_reference",
]