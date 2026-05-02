"""Agent module router — streaming AI helpers gated by RBAC + rate limit + budget.

Three layers of protection:
  1. JWT + RBAC          — require_module_permission("DQ", "write")
  2. Rate limit          — SlowAPI: 10/min, 100/day per user
  3. Daily output budget — pre-flight in service.py (CDP-AGT-0077)
"""

import json
import logging
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from sqlalchemy.orm import Session

from app.auth.rbac import require_module_permission
from app.common.models import User
from app.core.database import db_session
from app.core.errors import AppError

from .schemas import GenerateBusinessRuleRequest
from .service import AgentService

logger = logging.getLogger(__name__)


def _user_key(request: Request) -> str:
    """Per-user rate limit key. Hashes the JWT to avoid leaking it."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        import hashlib
        h = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
        return f"jwt:{h}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


limiter = Limiter(key_func=_user_key, default_limits=[])

MODULE_CODE = "DQ"
router = APIRouter(prefix="/api/agent", tags=["agent"])
write_required = require_module_permission(MODULE_CODE, permission="write")


@router.post("/dq/business-rule/stream")
@limiter.limit("10/minute;100/day")
async def stream_business_rule(
    request: Request,
    data: GenerateBusinessRuleRequest,
    db:   Annotated[Session, Depends(db_session)],
    user: Annotated[User, Depends(write_required)],
):
    """Stream the LLM output for a business rule.

    Response is text/event-stream. Events:
        event: thread       data: {"thread_id":"..."}
        event: step         data: {"phase":"Drafting rule","node":"draft_rule"}
        event: delta        data: {"text":"..."}
        event: tool         data: {"name":"...","direction":"request"}     (Phase 2)
        event: completed    data: {"duration_ms":1234}

    On error:
        event: error        data: {"code":"CDP-AGT-...","message":"..."}
    """
    svc = AgentService(db)

    async def event_source() -> AsyncIterator[bytes]:
        try:
            async for ev in svc.stream_business_rule(
                user=user,
                description=data.description,
                thread_id=data.thread_id,
            ):
                kind = ev.pop("type")
                yield _sse(kind, ev)
        except AppError as e:
            yield _sse("error", {"code": e.code, "message": e.message})

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n".encode("utf-8")
