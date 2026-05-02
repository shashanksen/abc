"""Admin operational endpoints.

Sits alongside admin.py — same patterns (BaseService, AppError, AuditService,
require_admin) so anyone reading admin.py can read this file too.

Endpoints:
  GET  /api/admin/activity                  recent feed across all users
  GET  /api/admin/users/{user_id}/journey   full per-user timeline
  GET  /api/admin/agent/tasks               recent agent task_log entries
  GET  /api/admin/agent/usage               daily char usage by user
  GET  /api/admin/agent/kill-switch         current kill-switch state
  POST /api/admin/agent/kill-switch         toggle kill-switch on/off

The activity feed and user journey draw from three tables:
  - core.user_activity   (logins, module views — written by AuditService.record_activity)
  - core.audit_log       (every state change   — written by AuditService.record)
  - agent.task_log       (every agent run      — written by AgentService)

We unify them in Python rather than via a SQL UNION because the columns
differ enough that a UNION would need a lot of NULL-padding and CASE casts.
The dataset per page is small (a few hundred rows max), so application-side
merge-and-sort is faster to write and easy to reason about.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from app.auth.auth import require_admin
from app.common.audit import AuditService
from app.common.models import (
    AuditLog, FeatureFlag, User, UserActivity,
)
from app.core.base import BaseService
from app.core.database import db_session
from app.core.errors import AppError


# ═══════════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════════
class ActivityItem(BaseModel):
    """One row in the unified activity feed.

    Source is one of "ACTIVITY", "AUDIT", "AGENT" so the UI can render
    different icons/colors. Everything else is normalized.
    """
    source:        str           # ACTIVITY | AUDIT | AGENT
    when:          datetime
    user_id:       UUID | None
    user_email:    str | None
    summary:       str           # human-readable one-liner
    detail:        dict[str, Any] | None = None


class ActivityFeedResponse(BaseModel):
    items: list[ActivityItem]
    next_before: datetime | None  # cursor for pagination (oldest item's `when`)


class UserJourneyResponse(BaseModel):
    user: dict[str, Any]
    items: list[ActivityItem]


class AgentTaskItem(BaseModel):
    id:            UUID
    user_id:       UUID
    user_email:    str | None
    skill_id:      str
    thread_id:     str | None
    state:         str
    duration_ms:   int | None
    output_chars:  int | None
    error:         str | None
    started_at:    datetime
    finished_at:   datetime | None


class AgentUsageRow(BaseModel):
    user_id:       UUID
    user_email:    str
    task_count:    int
    total_chars:   int
    failure_count: int


class KillSwitchState(BaseModel):
    enabled:     bool
    description: str | None
    updated_by:  UUID | None
    updated_at:  datetime


class KillSwitchToggle(BaseModel):
    enabled: bool


# ═══════════════════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════════════════
class AdminOpsService(BaseService):
    """Read-mostly service for admin ops views.

    All methods are admin-only. The route layer enforces require_admin;
    the service trusts that.
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.audit = AuditService(db)

    # ─── Unified activity feed ────────────────────────────────────────────────
    def activity_feed(self, *, limit: int, before: datetime | None = None) -> ActivityFeedResponse:
        """Return the most recent activity across all sources.

        Strategy: pull `limit` rows from each source, merge on `when`,
        slice to `limit`. With limit=50, we read 150 rows total.
        Cheap on indexed timestamps. The activity_user_time, audit_actor,
        and agent task_log indexes (created in the migrations) all cover
        ORDER BY started_at DESC.
        """
        cutoff = before or datetime.now(timezone.utc)

        # core.user_activity
        activity_rows = self.db.execute(
            select(UserActivity, User.email)
            .outerjoin(User, User.id == UserActivity.user_id)
            .where(UserActivity.created_at < cutoff)
            .order_by(UserActivity.created_at.desc())
            .limit(limit)
        ).all()

        items: list[ActivityItem] = [
            ActivityItem(
                source="ACTIVITY",
                when=row.UserActivity.created_at,
                user_id=row.UserActivity.user_id,
                user_email=row.email,
                summary=_summarize_activity(row.UserActivity),
                detail={
                    "type": row.UserActivity.activity_type,
                    "module": row.UserActivity.module_code,
                    "feature": row.UserActivity.feature_code,
                    "ip": str(row.UserActivity.ip_address) if row.UserActivity.ip_address else None,
                },
            )
            for row in activity_rows
        ]

        # core.audit_log
        audit_rows = self.db.execute(
            select(AuditLog)
            .where(AuditLog.created_at < cutoff)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).scalars().all()

        items.extend(
            ActivityItem(
                source="AUDIT",
                when=row.created_at,
                user_id=row.actor_id,
                user_email=row.actor_email,
                summary=_summarize_audit(row),
                detail={
                    "action": row.action,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                },
            )
            for row in audit_rows
        )

        # agent.task_log — read with raw SQL since the ORM model lives in
        # the agent module and importing it here would create a cross-module
        # dependency. JOIN to users for the email.
        agent_rows = self.db.execute(
            text("""
                SELECT t.id, t.user_id, u.email, t.skill_id, t.state,
                       t.duration_ms, t.output_chars, t.error,
                       t.started_at, t.finished_at
                FROM   agent.task_log t
                LEFT JOIN core.users u ON u.id = t.user_id
                WHERE  t.started_at < :cutoff
                ORDER  BY t.started_at DESC
                LIMIT  :lim
            """),
            {"cutoff": cutoff, "lim": limit},
        ).all()

        items.extend(
            ActivityItem(
                source="AGENT",
                when=row.started_at,
                user_id=row.user_id,
                user_email=row.email,
                summary=_summarize_agent_task(row),
                detail={
                    "skill_id": row.skill_id,
                    "state": row.state,
                    "duration_ms": row.duration_ms,
                    "output_chars": row.output_chars,
                    "error": row.error,
                },
            )
            for row in agent_rows
        )

        # Merge + sort + slice
        items.sort(key=lambda it: it.when, reverse=True)
        items = items[:limit]

        next_before = items[-1].when if len(items) == limit else None
        return ActivityFeedResponse(items=items, next_before=next_before)

    # ─── Per-user journey ─────────────────────────────────────────────────────
    def user_journey(self, *, user_id: UUID, limit: int = 200) -> UserJourneyResponse:
        """All events for one user, newest first.

        Cap at 200 — for full history, ops can query the DB directly.
        """
        u = self.db.get(User, user_id)
        if u is None:
            raise AppError("CDP-USR-0010")

        items: list[ActivityItem] = []

        for activity in self.db.scalars(
            select(UserActivity)
            .where(UserActivity.user_id == user_id)
            .order_by(UserActivity.created_at.desc())
            .limit(limit)
        ).all():
            items.append(ActivityItem(
                source="ACTIVITY",
                when=activity.created_at,
                user_id=activity.user_id,
                user_email=u.email,
                summary=_summarize_activity(activity),
                detail={"type": activity.activity_type, "module": activity.module_code,
                        "feature": activity.feature_code,
                        "ip": str(activity.ip_address) if activity.ip_address else None},
            ))

        for audit in self.db.scalars(
            select(AuditLog)
            .where(AuditLog.actor_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).all():
            items.append(ActivityItem(
                source="AUDIT",
                when=audit.created_at,
                user_id=audit.actor_id,
                user_email=audit.actor_email,
                summary=_summarize_audit(audit),
                detail={"action": audit.action, "entity_type": audit.entity_type,
                        "entity_id": audit.entity_id},
            ))

        agent_rows = self.db.execute(
            text("""
                SELECT id, user_id, skill_id, state, duration_ms, output_chars,
                       error, started_at, finished_at
                FROM   agent.task_log
                WHERE  user_id = :uid
                ORDER  BY started_at DESC
                LIMIT  :lim
            """),
            {"uid": str(user_id), "lim": limit},
        ).all()

        for row in agent_rows:
            items.append(ActivityItem(
                source="AGENT",
                when=row.started_at,
                user_id=row.user_id,
                user_email=u.email,
                summary=_summarize_agent_task(row),
                detail={"skill_id": row.skill_id, "state": row.state,
                        "duration_ms": row.duration_ms, "output_chars": row.output_chars,
                        "error": row.error},
            ))

        items.sort(key=lambda it: it.when, reverse=True)
        items = items[:limit]

        return UserJourneyResponse(
            user={"id": str(u.id), "email": u.email, "full_name": u.full_name,
                  "is_admin": u.is_admin, "is_active": u.is_active,
                  "last_login_at": u.last_login_at},
            items=items,
        )

    # ─── Agent tasks (recent) ─────────────────────────────────────────────────
    def agent_tasks(self, *, limit: int, state: str | None = None) -> list[AgentTaskItem]:
        params: dict[str, Any] = {"lim": limit}
        where = ""
        if state:
            where = "WHERE t.state = :state"
            params["state"] = state

        rows = self.db.execute(
            text(f"""
                SELECT t.id, t.user_id, u.email AS user_email, t.skill_id, t.thread_id,
                       t.state, t.duration_ms, t.output_chars, t.error,
                       t.started_at, t.finished_at
                FROM   agent.task_log t
                LEFT JOIN core.users u ON u.id = t.user_id
                {where}
                ORDER  BY t.started_at DESC
                LIMIT  :lim
            """),
            params,
        ).all()

        return [
            AgentTaskItem(
                id=row.id, user_id=row.user_id, user_email=row.user_email,
                skill_id=row.skill_id, thread_id=row.thread_id, state=row.state,
                duration_ms=row.duration_ms, output_chars=row.output_chars,
                error=row.error, started_at=row.started_at, finished_at=row.finished_at,
            )
            for row in rows
        ]

    # ─── Daily usage by user ──────────────────────────────────────────────────
    def daily_usage(self, *, top: int = 20) -> list[AgentUsageRow]:
        """Per-user usage today. Sorted by total_chars DESC.

        Designed for spotting heavy users / runaways. Reads the
        agent.daily_usage view created in 03_agent.sql.
        """
        rows = self.db.execute(
            text("""
                SELECT v.user_id, u.email AS user_email,
                       v.task_count, v.total_output_chars AS total_chars, v.failure_count
                FROM   agent.daily_usage v
                JOIN   core.users u ON u.id = v.user_id
                WHERE  v.day = date_trunc('day', NOW())
                ORDER  BY v.total_output_chars DESC
                LIMIT  :lim
            """),
            {"lim": top},
        ).all()

        return [
            AgentUsageRow(
                user_id=row.user_id, user_email=row.user_email,
                task_count=row.task_count, total_chars=row.total_chars,
                failure_count=row.failure_count,
            )
            for row in rows
        ]

    # ─── Kill-switch ──────────────────────────────────────────────────────────
    def get_kill_switch(self) -> KillSwitchState:
        flag = self.db.get(FeatureFlag, "agent.kill_switch")
        if flag is None:
            # Migration didn't seed; return the safe default.
            return KillSwitchState(
                enabled=False, description=None, updated_by=None,
                updated_at=datetime.now(timezone.utc),
            )
        return KillSwitchState(
            enabled=flag.enabled, description=flag.description,
            updated_by=flag.updated_by, updated_at=flag.updated_at,
        )

    def set_kill_switch(self, *, admin: User, enabled: bool) -> KillSwitchState:
        """Toggle the kill-switch. Audit-logged."""
        flag = self.db.get(FeatureFlag, "agent.kill_switch")
        if flag is None:
            flag = FeatureFlag(code="agent.kill_switch", enabled=enabled)
            self.db.add(flag)
        before_enabled = flag.enabled
        flag.enabled = enabled
        flag.updated_by = admin.id
        flag.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        self.audit.record(
            action="AGENT_KILL_SWITCH_TOGGLED",
            entity_type="FEATURE_FLAG",
            entity_id="agent.kill_switch",
            actor_id=admin.id, actor_email=admin.email,
            before_state={"enabled": before_enabled},
            after_state={"enabled": enabled},
        )
        return self.get_kill_switch()


# ═══════════════════════════════════════════════════════════════════════════════
# Summary helpers (UI-friendly one-liners)
# ═══════════════════════════════════════════════════════════════════════════════
def _summarize_activity(a: UserActivity) -> str:
    if a.activity_type == "LOGIN":
        return "Logged in"
    if a.activity_type == "MODULE_VIEW":
        return f"Opened {a.module_code} module" + (f" / {a.feature_code}" if a.feature_code else "")
    if a.activity_type == "FEATURE_USE":
        return f"Used {a.module_code or '?'} / {a.feature_code or '?'}"
    return a.activity_type


def _summarize_audit(a: AuditLog) -> str:
    # Map common actions to friendly text. Falls back to raw action.
    friendly = {
        "USER_REGISTERED":             "Registered",
        "USER_LOGIN":                  "Logged in",
        "USER_LOGIN_FAILED":           "Login failed",
        "ACCESS_REQUESTED":            "Requested access",
        "ACCESS_APPROVED":             "Access approved",
        "ACCESS_DENIED":               "Access denied",
        "ACCESS_GRANTED":              "Access granted",
        "AGENT_SKILL_INVOKED":         "Started agent run",
        "AGENT_KILL_SWITCH_TOGGLED":   "Toggled agent kill-switch",
        "DQ_DIMENSION_CREATED":        "Created DQ dimension",
        "DQ_DIMENSION_UPDATED":        "Updated DQ dimension",
        "DQ_BUSINESS_RULE_CREATED":    "Created DQ business rule",
        "DQ_TECHNICAL_RULE_CREATED":   "Created DQ technical rule",
    }
    base = friendly.get(a.action, a.action)
    if a.entity_type and a.entity_id:
        return f"{base} ({a.entity_type})"
    return base


def _summarize_agent_task(row: Any) -> str:
    """Summarize an agent.task_log row. `row` is a SQLAlchemy Row, not a model."""
    state_label = {
        "completed": "Agent run completed",
        "failed":    "Agent run failed",
        "submitted": "Agent run started",
        "working":   "Agent run in progress",
    }.get(row.state, f"Agent run: {row.state}")
    if row.skill_id:
        state_label = f"{state_label} ({row.skill_id})"
    return state_label


# ═══════════════════════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════════════════════
admin_ops_router = APIRouter(prefix="/api/admin", tags=["admin-ops"])


# ─── Activity feed ────────────────────────────────────────────────────────────
@admin_ops_router.get("/activity", response_model=ActivityFeedResponse)
def get_activity(
    db:     Annotated[Session, Depends(db_session)],
    _admin: Annotated[User, Depends(require_admin)],
    limit:  int = Query(50, ge=1, le=200),
    before: datetime | None = Query(None, description="Cursor — pass next_before from previous response"),
):
    return AdminOpsService(db).activity_feed(limit=limit, before=before)


# ─── Per-user journey ─────────────────────────────────────────────────────────
@admin_ops_router.get("/users/{user_id}/journey", response_model=UserJourneyResponse)
def get_user_journey(
    user_id: UUID,
    db:      Annotated[Session, Depends(db_session)],
    _admin:  Annotated[User, Depends(require_admin)],
    limit:   int = Query(200, ge=1, le=1000),
):
    return AdminOpsService(db).user_journey(user_id=user_id, limit=limit)


# ─── Agent ops ────────────────────────────────────────────────────────────────
@admin_ops_router.get("/agent/tasks", response_model=list[AgentTaskItem])
def list_agent_tasks(
    db:     Annotated[Session, Depends(db_session)],
    _admin: Annotated[User, Depends(require_admin)],
    limit:  int = Query(100, ge=1, le=500),
    state:  str | None = Query(None, regex="^(submitted|working|completed|failed)$"),
):
    return AdminOpsService(db).agent_tasks(limit=limit, state=state)


@admin_ops_router.get("/agent/usage", response_model=list[AgentUsageRow])
def get_agent_usage(
    db:     Annotated[Session, Depends(db_session)],
    _admin: Annotated[User, Depends(require_admin)],
    top:    int = Query(20, ge=1, le=100),
):
    return AdminOpsService(db).daily_usage(top=top)


@admin_ops_router.get("/agent/kill-switch", response_model=KillSwitchState)
def get_kill_switch(
    db:     Annotated[Session, Depends(db_session)],
    _admin: Annotated[User, Depends(require_admin)],
):
    return AdminOpsService(db).get_kill_switch()


@admin_ops_router.post("/agent/kill-switch", response_model=KillSwitchState)
def toggle_kill_switch(
    body:   KillSwitchToggle,
    db:     Annotated[Session, Depends(db_session)],
    admin:  Annotated[User, Depends(require_admin)],
):
    return AdminOpsService(db).set_kill_switch(admin=admin, enabled=body.enabled)
