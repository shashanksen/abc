"""Password hashing + JWT encode/decode.

JWT keys (split):
  - jwt_user_session_key       signs and verifies user access tokens
  - jwt_user_session_key_legacy verify-only, accepted during migration windows
  - jwt_agent_callback_key     signs and verifies short-lived on-behalf-of tokens
                               (no legacy fallback; 5-min TTL)

Soft migration: after a key rotation, the legacy key stays in the secret for
the 8-hour access-token TTL window. After the window, all in-flight tokens
have expired naturally and the legacy key can be removed.

Token type routing in decode_token:
  - type=access            → user_session_key (+ legacy fallback)
  - type=agent_callback    → agent_callback_key (no legacy)
  - other                  → user_session_key (+ legacy fallback)  [back-compat]
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AppError


_settings = get_settings()


# ─── Password hashing ─────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    pwd_bytes = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ─── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(*, subject: str, claims: dict[str, Any] | None = None) -> str:
    """Sign a user session token with the active user_session key."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=_settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    if claims:
        payload.update(claims)
    return jwt.encode(
        payload,
        _settings.jwt_user_session_key,
        algorithm=_settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Verify and decode. Routes by `type` claim to the right key."""
    try:
        unverified = jwt.get_unverified_claims(token)
    except JWTError as e:
        raise AppError("CDP-AUT-0003", detail=str(e)) from e

    token_type = unverified.get("type")

    if token_type == "agent_callback":
        return _verify_with_keys(token, [_settings.jwt_agent_callback_key])

    # Default path: user access tokens. Includes legacy fallback during migration.
    return _verify_with_keys(
        token,
        [_settings.jwt_user_session_key, _settings.jwt_user_session_key_legacy],
    )


def _verify_with_keys(token: str, candidate_keys: list[str | None]) -> dict[str, Any]:
    """Try each non-None key in order. Last error wins."""
    last_error: Exception | None = None
    for key in candidate_keys:
        if not key:
            continue
        try:
            return jwt.decode(token, key, algorithms=[_settings.jwt_algorithm])
        except jwt.ExpiredSignatureError as e:
            # Expired is definite — don't try other keys.
            raise AppError("CDP-AUT-0002") from e
        except JWTError as e:
            last_error = e
            continue

    raise AppError("CDP-AUT-0003", detail=str(last_error) if last_error else "no key matched")


# ─── On-behalf-of token minting ───────────────────────────────────────────────
def create_agent_callback_token(
    *,
    user_id: str,
    user_email: str,
    module: str,
    permission: str,
    ttl_minutes: int = 5,
) -> str:
    """Issue a short-lived JWT for agent tool callbacks.

    Carries:
      - sub:    user_id (audit trace)
      - email:  user email
      - type:   "agent_callback"
      - scope:  f"{MODULE}:{permission}"  (enforced by RBAC dependency)
      - exp:    5 minutes from now
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": user_email,
        "type": "agent_callback",
        "scope": f"{module.upper()}:{permission}",
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(payload, _settings.jwt_agent_callback_key, algorithm=_settings.jwt_algorithm)
