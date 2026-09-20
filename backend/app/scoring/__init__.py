"""Rule-based complaint scoring (P2 add-on).

Public API
----------
* :class:`~app.scoring.scoring.ComplaintFacts` - minimal complaint shape the
  scorers accept (pure, ORM-free).
* :class:`~app.scoring.scoring.Score` - the deterministic low/medium/high level
  plus its plain-English rationale.
* :func:`~app.scoring.scoring.calculate_trust_score` - is this report likely
  genuine, or spam / a duplicate filing?
* :func:`~app.scoring.scoring.calculate_priority` - how urgently should the
  report be handled?

The implementation deliberately lives in the ``__all__`` module so it stays a
pure, testable unit with no database or clock in its import path.
"""
from __future__ import annotations

from app.scoring.scoring import (
    ComplaintFacts,
    RECENT_WINDOW,
    Score,
    calculate_priority,
    calculate_trust_score,
)

__all__ = [
    "ComplaintFacts",
    "RECENT_WINDOW",
    "Score",
    "calculate_priority",
    "calculate_trust_score",
]
