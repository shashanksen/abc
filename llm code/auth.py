"""Shared-secret bearer auth for the A2A agent.

The FastAPI backend sends `Authorization: Bearer <AGENT_SHARED_SECRET>`.
Both sides read the same value from env. Rotate by updating both env vars
and redeploying. Phase-2 hardening swap: replace with OAuth M2M.
"""
from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


def _expected_secret() -> str:
    secret = os.getenv("AGENT_SHARED_SECRET")
    if not secret:
        raise RuntimeError("AGENT_SHARED_SECRET env var is not set")
    return secret


def verify_bearer(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    presented = authorization.split(" ", 1)[1].strip()
    if not hmac.compare_digest(presented, _expected_secret()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )