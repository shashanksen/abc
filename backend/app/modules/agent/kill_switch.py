"""Agent kill-switch — pre-flight check.

Reads core.feature_flags.agent.kill_switch on every request. We deliberately
don't cache: the kill-switch is the one flag where a stale read is genuinely
bad (an incident is in progress; admins flipped the switch; they expect
requests to start failing immediately).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.models import FeatureFlag
from app.core.errors import AppError


def assert_agent_enabled(db: Session) -> None:
    """Raise CDP-AGT-0080 if the platform-wide agent kill-switch is ON."""
    flag = db.get(FeatureFlag, "agent.kill_switch")
    if flag is None:
        # Migration 05 should have seeded this. Fail safe and allow.
        return
    if flag.enabled is True:
        raise AppError(
            "CDP-AGT-0080",
            detail="Agent functionality is currently disabled by an administrator.",
        )
