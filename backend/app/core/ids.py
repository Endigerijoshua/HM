"""Deterministic collision-resistant reference ID helpers.

IDs are compact, human-auditable tokens of the form ``PREFIX-YYYYMMDD-hex``.
They are used to cross-reference routing decisions, complaints, conflicts,
scenarios and audit events without leaking internal integer keys.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone


def new_reference(prefix: str, entropy_bytes: int = 4) -> str:
    """Generate a short auditable reference ID."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    token = secrets.token_hex(entropy_bytes)
    return f"{prefix}-{stamp}-{token}"


def complaint_public_ref(seed: int) -> str:
    """Stable public reference for seeded demo complaints."""
    return f"C-{seed:04d}"


def route_reference() -> str:
    return new_reference("RT")


def conflict_reference() -> str:
    return new_reference("CF")


def scenario_reference() -> str:
    return new_reference("SC")


def migration_plan_reference() -> str:
    return new_reference("MP")