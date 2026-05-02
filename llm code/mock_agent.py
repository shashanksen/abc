"""Local mock — emits the same SSE events the LangGraph version does.

Use during frontend development to avoid spinning up Databricks + Postgres
checkpointer just to see the streaming UI work. The "orchestrator" simulates
two phases (Drafting rule) so you can see the `step` event flow into the UI.

Run:
    AGENT_SHARED_SECRET=dev-secret-not-for-prod \\
    uvicorn mock_agent:app --port 8001
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from auth import verify_bearer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("a2a-mock")

app = FastAPI(title="CDP DQ Agent — LOCAL MOCK")


_MOCK_RESPONSE = (
    "The rule checks that the customer email field is populated for every "
    "active account in the customers table. A row passes when email is "
    "non-null, non-empty after trim, and contains a single '@' character. "
    "Inactive accounts (status != 'ACTIVE') are excluded from the check."
)


@app.get("/.well-known/agent.json")
def agent_card() -> dict[str, Any]:
    return {
        "name": "CDP DQ Agent (mock)",
        "description": "Local mock — does not call any LLM.",
        "url": os.getenv("AGENT_PUBLIC_URL", "http://localhost:8001"),
        "version": "0.2.0-mock",
        "protocolVersion": "0.2.0",
        "capabilities": {"streaming": True, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {"id": "generate_business_rule", "name": "Generate business rule",
             "description": "Mock — returns a canned rule.", "tags": ["dq", "rules", "mock"]},
        ],
    }


@app.post("/", dependencies=[Depends(verify_bearer)])
async def jsonrpc(request: Request):
    body = await request.json()
    if body.get("method") == "message/stream":
        return StreamingResponse(
            _stream(body.get("params") or {}),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    return JSONResponse(
        content={"jsonrpc": "2.0", "id": body.get("id"),
                 "error": {"code": -32601, "message": "method not found"}},
    )


async def _stream(params: dict[str, Any]) -> AsyncIterator[bytes]:
    task_id = str(uuid.uuid4())
    message = params.get("message") or {}
    metadata = message.get("metadata") or {}
    skill_id = metadata.get("skill_id")

    if skill_id != "generate_business_rule":
        yield _sse("status-update", {"taskId": task_id, "state": "failed",
                                      "error": f"unknown skill: {skill_id}"})
        return

    # ─── Submitted / working ─────────────────────────────────────────────
    yield _sse("status-update", {"taskId": task_id, "state": "submitted"})
    await asyncio.sleep(0.05)
    yield _sse("status-update", {"taskId": task_id, "state": "working"})

    # ─── Step: drafting (the only Phase 1 node) ──────────────────────────
    yield _sse("step", {"taskId": task_id, "phase": "Drafting rule", "node": "draft_rule"})
    await asyncio.sleep(0.15)

    # Stream the canned response a few words at a time.
    words = _MOCK_RESPONSE.split(" ")
    for i in range(0, len(words), 3):
        chunk = " ".join(words[i:i + 3])
        if i + 3 < len(words):
            chunk += " "
        yield _sse("artifact-update", {"taskId": task_id, "delta": chunk})
        await asyncio.sleep(0.07)

    yield _sse("status-update", {"taskId": task_id, "state": "completed"})


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n".encode("utf-8")
