"""Per-user daily budget for agent skills.

Pre-flight check: before sending the A2A request, sum today's output
characters from agent.task_log for this user. If the sum exceeds the
configured cap, refuse with CDP-AGT-0077.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError


def assert_within_daily_budget(db: Session, *, user_id: UUID) -> None:
    """Raise CDP-AGT-0077 if the user has hit their daily output budget."""
    cap = int(os.getenv("AGENT_DAILY_CHAR_BUDGET", "500000"))

    from .service import AgentTaskLog

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    used = db.scalar(
        select(func.coalesce(func.sum(AgentTaskLog.output_chars), 0))
        .where(AgentTaskLog.user_id == user_id)
        .where(AgentTaskLog.started_at >= today_start)
    ) or 0

    if used >= cap:
        raise AppError(
            "CDP-AGT-0077",
            detail=f"Used {used} of {cap} characters today.",
            context={"used": used, "limit": cap},
        )
