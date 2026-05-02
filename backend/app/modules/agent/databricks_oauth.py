"""Databricks OAuth M2M token cache.

Replaces the static AGENT_SHARED_SECRET. Tokens auto-rotate. Refreshes
proactively at ~50 minutes; single-flight via asyncio.Lock.

# VERIFY against current Databricks docs:
#   - OAuth token endpoint URL shape (account-level)
#   - Request body field names (we use grant_type, scope)
#   - Response field names (we use access_token, expires_in)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)


_REFRESH_THRESHOLD_SECONDS = 600


@dataclass
class _CachedToken:
    access_token: str
    expires_at_monotonic: float

    @property
    def remaining_seconds(self) -> float:
        return self.expires_at_monotonic - time.monotonic()

    def needs_refresh(self) -> bool:
        return self.remaining_seconds < _REFRESH_THRESHOLD_SECONDS


class DatabricksOAuthClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache: _CachedToken | None = None
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        if self._cache is None or self._cache.needs_refresh():
            await self._refresh()
        assert self._cache is not None
        return self._cache.access_token

    async def _refresh(self) -> None:
        async with self._lock:
            if self._cache is not None and not self._cache.needs_refresh():
                return

            client_id = self._settings.databricks_oauth_client_id
            client_secret = self._settings.databricks_oauth_client_secret
            token_endpoint = self._settings.databricks_oauth_token_endpoint

            data = {
                "grant_type": "client_credentials",
                "scope": "all-apis",     # narrow if your SP supports finer scopes
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as c:
                    resp = await c.post(
                        token_endpoint,
                        data=data,
                        auth=(client_id, client_secret),
                        headers={"Accept": "application/json"},
                    )
            except httpx.RequestError as e:
                if self._cache is not None:
                    logger.warning("OAuth refresh failed, serving cached: %s", e)
                    return
                raise AppError("CDP-AGT-0070", detail=f"OAuth token endpoint unreachable: {e}") from e

            if resp.status_code != 200:
                preview = resp.text[:300]
                logger.error("OAuth refresh got %d: %s", resp.status_code, preview)
                if self._cache is not None:
                    return
                raise AppError(
                    "CDP-AGT-0071",
                    detail=f"OAuth token endpoint returned {resp.status_code}",
                    context={"body_preview": preview},
                )

            payload = resp.json()
            access_token = payload.get("access_token")
            expires_in = payload.get("expires_in", 3600)
            if not access_token:
                raise AppError("CDP-AGT-0072", detail="OAuth response missing access_token")

            self._cache = _CachedToken(
                access_token=access_token,
                expires_at_monotonic=time.monotonic() + expires_in,
            )
            logger.info("OAuth token refreshed (expires in %ds)", expires_in)


_client: DatabricksOAuthClient | None = None


def get_oauth_client() -> DatabricksOAuthClient:
    global _client
    if _client is None:
        _client = DatabricksOAuthClient()
    return _client


async def get_oauth_token() -> str:
    return await get_oauth_client().get_token()
