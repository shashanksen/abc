"""A2A streaming client.

Uses Databricks OAuth M2M for production. Local dev can override with a
static bearer via AGENT_BEARER_OVERRIDE env var (used with mock_agent.py).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import AsyncIterator

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

from .databricks_oauth import get_oauth_token

logger = logging.getLogger(__name__)


class A2AClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.databricks_agent_base_url).rstrip("/")
        self._timeout = timeout_seconds or float(os.getenv("AGENT_REQUEST_TIMEOUT_SECONDS", "180"))
        self._bearer_override = os.getenv("AGENT_BEARER_OVERRIDE")
        if not self._base_url:
            raise AppError("CDP-SYS-0091", detail="databricks_agent_base_url not configured")

    async def _bearer(self) -> str:
        """Resolve the bearer to use for this outbound request."""
        if self._bearer_override:
            return self._bearer_override
        return await get_oauth_token()

    async def message_stream(
        self,
        *,
        skill_id: str,
        text: str,
        thread_id: str,
        on_behalf_of_token: str,
        user_id: str,
    ) -> AsyncIterator[tuple[str, dict]]:
        message = {
            "messageId": str(uuid.uuid4()),
            "role": "user",
            "kind": "message",
            "contextId": thread_id,
            "parts": [{"kind": "text", "text": text}],
            "metadata": {
                "skill_id": skill_id,
                "on_behalf_of_token": on_behalf_of_token,
                "user_id": user_id,
            },
        }
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/stream",
            "params": {"message": message},
        }
        headers = {
            "Authorization": f"Bearer {await self._bearer()}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as c:
                async with c.stream("POST", self._base_url + "/", json=payload, headers=headers) as resp:
                    if resp.status_code == 401:
                        raise AppError("CDP-AGT-0071")
                    if resp.status_code >= 500:
                        raise AppError("CDP-AGT-0070", context={"status": resp.status_code})
                    if resp.status_code != 200:
                        body_preview = (await resp.aread()).decode(errors="replace")[:300]
                        raise AppError(
                            "CDP-AGT-0072",
                            detail=f"HTTP {resp.status_code}",
                            context={"body_preview": body_preview},
                        )
                    async for event_name, data in self._parse_sse(resp.aiter_lines()):
                        yield event_name, data

        except httpx.TimeoutException as e:
            raise AppError("CDP-AGT-0074", detail=str(e)) from e
        except httpx.RequestError as e:
            raise AppError("CDP-AGT-0070", detail=str(e)) from e

    @staticmethod
    async def _parse_sse(lines: AsyncIterator[str]) -> AsyncIterator[tuple[str, dict]]:
        event_name: str | None = None
        data_lines: list[str] = []

        async for line in lines:
            if line == "":
                if event_name and data_lines:
                    raw = "\n".join(data_lines)
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("agent SSE: non-JSON data on event=%s", event_name)
                        event_name, data_lines = None, []
                        continue
                    yield event_name, parsed
                event_name, data_lines = None, []
                continue

            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].lstrip())
