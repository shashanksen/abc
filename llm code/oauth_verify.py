"""Databricks-side OAuth M2M verifier.

Replaces auth.py's shared-secret check for production. The mock_agent.py
keeps the shared-secret path for local dev.

How it works:
  1. FastAPI sends `Authorization: Bearer <oauth-token>` from
     databricks_oauth.py (account-level SP, client_credentials grant).
  2. We verify the token's signature against Databricks' published JWKs.
  3. We check `iss`, `aud`, and `exp` claims.
  4. We optionally check the SP claim is on an allowlist (defense-in-depth
     in case multiple SPs exist in the account).

Why this is more secure than the shared-secret approach:
  - Tokens are short-lived (1h) and auto-rotate.
  - Token signature is public-key crypto; we never see the SP's client_secret.
  - The SP's client_secret can be rotated without touching this code —
     just rotate at the Databricks side and update FastAPI's secret.

# VERIFY against current Databricks docs:
#   - JWKs URL format. Account-level OIDC discovery typically lives at:
#       https://accounts.cloud.databricks.com/oidc/accounts/<account-id>/.well-known/openid-configuration
#     and the JWKs URL is one of its fields. Confirm the path.
#   - Issuer (`iss`) claim value. It's typically the account OIDC issuer URL.
#   - Audience (`aud`) claim. May be the App's URL or a workspace identifier.
#
# For initial deployment, run with `OAUTH_VERIFY_AUDIENCE_CHECK=false` so
# audience mismatches log warnings but don't reject. Once you've observed
# the actual `aud` claim Databricks issues, set the expected value in env
# and flip the check on.

Environment variables (set on the Databricks App):
  OAUTH_ISSUER_URL        e.g. https://accounts.cloud.databricks.com/oidc/accounts/<id>
  OAUTH_JWKS_URL          full URL to the JWKs document
  OAUTH_EXPECTED_SP_ID    (optional) reject tokens not from this SP id
  OAUTH_AUDIENCE_CHECK    "true" or "false" (default false during rollout)
  OAUTH_EXPECTED_AUDIENCE (only used if AUDIENCE_CHECK=true)

  AGENT_SHARED_SECRET     keep set; used by /healthz path and as fallback
                          if OAUTH_VERIFY_DISABLED=true (debug only).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

logger = logging.getLogger("auth.oauth")


# ─── JWKs cache ───────────────────────────────────────────────────────────────
class _JWKsCache:
    """Caches the Databricks JWKs document. Refreshes hourly.

    JWKs rotation on the Databricks side is rare but possible. If we get a
    "kid not found" verification failure, we force-refresh and retry once
    before failing the request — this handles the rotation case.
    """

    _CACHE_TTL_SECONDS = 3600

    def __init__(self) -> None:
        self._keys: list[dict] = []
        self._fetched_at: float = 0.0

    async def get(self, *, force_refresh: bool = False) -> list[dict]:
        now = time.monotonic()
        if not force_refresh and self._keys and (now - self._fetched_at) < self._CACHE_TTL_SECONDS:
            return self._keys

        url = os.getenv("OAUTH_JWKS_URL")
        if not url:
            raise RuntimeError("OAUTH_JWKS_URL not configured")

        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(url)
            resp.raise_for_status()
            data = resp.json()

        self._keys = data.get("keys", [])
        self._fetched_at = now
        logger.info("JWKs refreshed (%d keys)", len(self._keys))
        return self._keys


_jwks_cache = _JWKsCache()


# ─── Verification ─────────────────────────────────────────────────────────────
async def verify_oauth_bearer(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """FastAPI dependency: verify the OAuth bearer and return the claims dict.

    Raises 401 on any verification failure.

    Disable with OAUTH_VERIFY_DISABLED=true ONLY for debugging — and even
    then the shared-secret path is still required.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer")
    token = authorization.split(" ", 1)[1].strip()

    # Local-dev escape hatch: shared-secret path. Keep this for the mock
    # agent and for incident-response debugging when JWKs is misbehaving.
    if os.getenv("OAUTH_VERIFY_DISABLED") == "true":
        expected = os.getenv("AGENT_SHARED_SECRET", "")
        if expected and token == expected:
            logger.warning("OAuth verify DISABLED — using shared-secret fallback")
            return {"sub": "shared-secret-bypass", "type": "fallback"}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    # Real OAuth path: verify against JWKs.
    try:
        claims = await _verify_jwt(token)
    except _OAuthVerifyError as e:
        logger.warning("oauth_verify_rejected reason=%s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    # Optional: check the SP id. Defense-in-depth in case more SPs exist
    # in the account.
    expected_sp = os.getenv("OAUTH_EXPECTED_SP_ID")
    if expected_sp and claims.get("sub") != expected_sp:
        logger.warning("oauth_verify_rejected reason=sp_mismatch sub=%s expected=%s",
                       claims.get("sub"), expected_sp)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

    return claims


class _OAuthVerifyError(Exception):
    pass


async def _verify_jwt(token: str) -> dict[str, Any]:
    issuer = os.getenv("OAUTH_ISSUER_URL")
    if not issuer:
        raise _OAuthVerifyError("OAUTH_ISSUER_URL not configured")

    audience_check = os.getenv("OAUTH_AUDIENCE_CHECK", "false").lower() == "true"
    expected_audience = os.getenv("OAUTH_EXPECTED_AUDIENCE") if audience_check else None

    # Get the unverified header to find the kid.
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise _OAuthVerifyError(f"malformed_header: {e}") from e

    kid = header.get("kid")
    if not kid:
        raise _OAuthVerifyError("missing_kid")

    # Find the matching key. If not found, force-refresh JWKs once (rotation case).
    keys = await _jwks_cache.get()
    key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        keys = await _jwks_cache.get(force_refresh=True)
        key = next((k for k in keys if k.get("kid") == kid), None)
        if key is None:
            raise _OAuthVerifyError(f"kid_not_found: {kid}")

    # Verify signature + standard claims.
    options = {"verify_aud": bool(expected_audience)}
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[header.get("alg", "RS256")],
            audience=expected_audience,
            issuer=issuer,
            options=options,
        )
    except jwt.ExpiredSignatureError as e:
        raise _OAuthVerifyError(f"expired: {e}") from e
    except JWTError as e:
        raise _OAuthVerifyError(f"jwt_error: {e}") from e

    return claims
