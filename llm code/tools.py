"""Authenticated callback tools.

Phase 1: this file is scaffolding only. No tools are registered with the
graph. The point of having it now is so adding the first tool in Phase 2
is mechanical:

  1. Write a function `def list_dimensions(...)` decorated with `@tool`.
  2. Bind it to the LLM in `agent.py`: `llm.bind_tools([list_dimensions])`.
  3. Add a "tools" node to the graph that calls them.

The CallbackClient class below is the auth pattern every tool will use.
It pulls the on-behalf-of JWT from the LangGraph RunnableConfig and uses
it as a bearer token when calling FastAPI. This means:

  - Tool calls hit the same endpoints as the UI (/api/dq/dimensions etc.)
  - RBAC is enforced — Alice's agent can only do what Alice can do.
  - Audit trail: actor_id is the user, not a service account.

The token is per-turn (5 min TTL) and never persisted to state — see
state.py for the rationale.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class ToolAuthError(Exception):
    """Raised when the on-behalf-of token is missing from config."""


class CallbackClient:
    """Thin httpx wrapper that injects the on-behalf-of token.

    Tools instantiate this from a `RunnableConfig` and call `.get` / `.post`
    on it. The class doesn't know about the FastAPI domain — that's the
    individual tool's job.
    """

    def __init__(self, *, token: str, base_url: str, timeout_seconds: float = 15.0) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    @classmethod
    def from_config(cls, config: RunnableConfig) -> "CallbackClient":
        cfg = (config or {}).get("configurable") or {}
        token = cfg.get("on_behalf_of_token")
        if not token:
            raise ToolAuthError(
                "on_behalf_of_token missing from RunnableConfig — FastAPI "
                "must mint and forward it for tool callbacks to work."
            )
        base_url = os.getenv("FASTAPI_CALLBACK_URL", "")
        if not base_url:
            raise ToolAuthError("FASTAPI_CALLBACK_URL not configured on the agent.")
        return cls(token=token, base_url=base_url)

    async def get(self, path: str, *, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            resp = await c.get(
                self._base_url + path,
                headers={"Authorization": f"Bearer {self._token}"},
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, *, json: dict) -> Any:
        async with httpx.AsyncClient(timeout=self._timeout) as c:
            resp = await c.post(
                self._base_url + path,
                headers={"Authorization": f"Bearer {self._token}"},
                json=json,
            )
            resp.raise_for_status()
            return resp.json()


# ─── Phase 2 tool sketches (do NOT enable in Phase 1) ─────────────────────────
# These are commented out deliberately. Uncomment + register with the graph
# when you're ready to give the agent autonomous read/write capability.
#
# from langchain_core.tools import tool
#
# @tool
# async def list_dimensions(config: RunnableConfig) -> list[dict]:
#     """Fetch all DQ dimensions the user has access to."""
#     client = CallbackClient.from_config(config)
#     return await client.get("/api/dq/dimensions")
#
# @tool
# async def save_draft_rule(
#     code: str, dimension_id: str | None, ede_mapping: str | None,
#     rule_text: str, config: RunnableConfig,
# ) -> dict:
#     """Persist a generated rule as a DRAFT business rule.
#
#     Same endpoint the UI hits; user permissions enforced by the on-behalf-of
#     token. The audit log will show actor=user, source=AGENT.
#     """
#     client = CallbackClient.from_config(config)
#     return await client.post("/api/dq/business-rules", json={
#         "code": code,
#         "dimension_id": dimension_id,
#         "ede_mapping": ede_mapping,
#         "rule_text": rule_text,
#     })
