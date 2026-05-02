"""AgentService — the heart of the agent module.

Pre-flight checks (in order):
  1. kill_switch        — platform-wide flag, fastest fail
  2. assert_safe_input  — prompt-injection layer 1 (input)
  3. budget             — daily char cap per user
  4. mint OBO token     — only after all checks pass

Post-flight check:
  validate_business_rule_text() runs on the full streamed output before we
  emit `completed`. Layer 3 of the prompt-injection defense.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Session

from app.common.audit import AuditService
from app.common.models import User
from app.core.base import BaseService
from app.core.database import Base
from app.core.errors import AppError
from app.core.security import create_agent_callback_token

from .budget import assert_within_daily_budget
from .client import A2AClient
from .kill_switch import assert_agent_enabled
from .output_validation import validate_business_rule_text
from .prompt_safety import assert_safe_input

logger = logging.getLogger(__name__)


# ─── ORM model for agent.task_log ─────────────────────────────────────────────
class AgentTaskLog(Base):
    __tablename__ = "task_log"
    __table_args__ = {"schema": "agent"}

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(PG_UUID(as_uuid=True), nullable=False)
    skill_id     = Column(String(64), nullable=False)
    thread_id    = Column(String(64))
    state        = Column(String(20), nullable=False)
    input_text   = Column(Text, nullable=False)
    output_text  = Column(Text)
    error        = Column(Text)
    duration_ms  = Column(Integer)
    output_chars = Column(Integer)
    metadata_    = Column("metadata", JSONB, default=dict)
    started_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at  = Column(DateTime(timezone=True))


class AgentService(BaseService):
    MODULE_CODE = "DQ"
    DEFAULT_PERMISSION = "write"

    def __init__(self, db: Session, *, client: A2AClient | None = None):
        super().__init__(db)
        self._client = client or A2AClient()
        self.audit = AuditService(db)

    async def stream_business_rule(
        self,
        *,
        user: User,
        description: str,
        thread_id: str | None = None,
    ) -> AsyncIterator[dict]:
        skill_id = "generate_business_rule"

        # ── Pre-flight: kill-switch ─────────────────────────────────────────
        assert_agent_enabled(self.db)

        # ── Pre-flight: prompt safety ───────────────────────────────────────
        description = assert_safe_input(description, user_id=user.id, context="agent.business_rule")

        # ── Pre-flight: daily budget ────────────────────────────────────────
        assert_within_daily_budget(self.db, user_id=user.id)

        # ── Mint on-behalf-of token (5 min, scoped to DQ:write) ─────────────
        callback_token = create_agent_callback_token(
            user_id=str(user.id),
            user_email=user.email,
            module=self.MODULE_CODE,
            permission=self.DEFAULT_PERMISSION,
        )

        # ── Persist task_log row ────────────────────────────────────────────
        thread_id = thread_id or str(uuid.uuid4())
        task_log = AgentTaskLog(
            user_id=user.id,
            skill_id=skill_id,
            thread_id=thread_id,
            state="submitted",
            input_text=description,
            metadata_={},
        )
        self.db.add(task_log)
        self.db.flush()

        self.audit.record(
            action="AGENT_SKILL_INVOKED",
            entity_type="AGENT_TASK",
            entity_id=task_log.id,
            actor_id=user.id, actor_email=user.email,
            after_state={"skill_id": skill_id, "input_chars": len(description), "thread_id": thread_id},
        )
        self.db.commit()

        # Inform UI of thread_id for refinement turns.
        yield {"type": "thread", "thread_id": thread_id}

        started = time.monotonic()
        collected: list[str] = []

        try:
            async for event_name, data in self._client.message_stream(
                skill_id=skill_id,
                text=description,
                thread_id=thread_id,
                on_behalf_of_token=callback_token,
                user_id=str(user.id),
            ):
                ui_event = _to_ui_event(event_name, data)
                if ui_event is None:
                    continue

                if ui_event["type"] == "delta":
                    collected.append(ui_event["text"])

                if ui_event["type"] == "error":
                    raise AppError(
                        ui_event.get("code") or "CDP-AGT-0073",
                        detail=ui_event.get("message"),
                    )

                yield ui_event

        except AppError as e:
            duration_ms = int((time.monotonic() - started) * 1000)
            task_log.state = "failed"
            task_log.error = f"[{e.code}] {e.message}: {e.detail or ''}".strip()
            task_log.duration_ms = duration_ms
            task_log.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            yield {"type": "error", "code": e.code, "message": e.message}
            return
        except Exception as e:
            logger.exception("unexpected error in stream_business_rule")
            duration_ms = int((time.monotonic() - started) * 1000)
            task_log.state = "failed"
            task_log.error = f"unexpected: {e}"
            task_log.duration_ms = duration_ms
            task_log.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            yield {"type": "error", "code": "CDP-SYS-0091", "message": "Unexpected error"}
            return

        duration_ms = int((time.monotonic() - started) * 1000)
        full_text = "".join(collected)

        # ── Post-flight: output validation (layer 3) ────────────────────────
        try:
            validate_business_rule_text(full_text)
        except AppError as e:
            task_log.state = "failed"
            task_log.error = f"output_validation: {e.code}"
            task_log.output_text = full_text
            task_log.output_chars = len(full_text)
            task_log.duration_ms = duration_ms
            task_log.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            yield {"type": "error", "code": e.code, "message": e.message}
            return

        task_log.output_text = full_text
        task_log.output_chars = len(full_text)
        task_log.duration_ms = duration_ms
        task_log.state = "completed"
        task_log.finished_at = datetime.now(timezone.utc)
        self.db.commit()

        yield {"type": "completed", "duration_ms": duration_ms}


# ─── A2A → UI event mapping ───────────────────────────────────────────────────
def _to_ui_event(event_name: str, data: dict) -> dict | None:
    if event_name == "artifact-update":
        delta = data.get("delta") or ""
        if delta:
            return {"type": "delta", "text": delta}
        return None

    if event_name == "step":
        return {
            "type": "step",
            "phase": data.get("phase", ""),
            "node": data.get("node"),
        }

    if event_name == "tool":
        return {
            "type": "tool",
            "name": data.get("name"),
            "direction": data.get("direction"),
            "summary": data.get("summary"),
        }

    if event_name == "status-update":
        state = data.get("state")
        if state == "failed":
            return {"type": "error", "code": "CDP-AGT-0073",
                    "message": data.get("error") or "Agent failed"}
        return None

    return None
