"""Audit service — call from any service when state changes."""
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.models import AuditLog, UserActivity


class AuditService:
    """Lightweight wrapper. Caller passes structured before/after states.

    Convention for `action`: SCREAMING_SNAKE_CASE verb.
       USER_LOGIN, USER_LOGIN_FAILED, USER_REGISTERED,
       ACCESS_REQUESTED, ACCESS_APPROVED, ACCESS_DENIED, ACCESS_REVOKED,
       MODULE_ENABLED, MODULE_DISABLED,
       DQ_DIMENSION_CREATED, DQ_DIMENSION_UPDATED, ...
    """

    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: Optional[str | UUID] = None,
        actor_id: Optional[UUID] = None,
        actor_email: Optional[str] = None,
        before_state: Optional[dict[str, Any]] = None,
        after_state: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            before_state=before_state,
            after_state=after_state,
            metadata_=metadata or {},
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def record_activity(
        self,
        *,
        user_id: UUID,
        activity_type: str,
        module_code: Optional[str] = None,
        feature_code: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> UserActivity:
        entry = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            module_code=module_code,
            feature_code=feature_code,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata or {},
        )
        self.db.add(entry)
        self.db.flush()
        return entry
