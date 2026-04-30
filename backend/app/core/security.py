"""Password hashing + JWT encode/decode."""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AppError


_settings = get_settings()


# ─── Password hashing (using bcrypt directly, no passlib) ─────────────────────
def hash_password(plain: str) -> str:
    """Hash a password using bcrypt. Returns the hash as a UTF-8 string."""
    # bcrypt has a hard 72-byte limit; truncate to be safe with multibyte chars
    pwd_bytes = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash. False on any error."""
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ─── JWT ──────────────────────────────────────────────────────────────────────
def create_access_token(*, subject: str, claims: dict[str, Any] | None = None) -> str:
    """Build a JWT. `subject` is typically the user UUID."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=_settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, _settings.jwt_secret_key, algorithm=_settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _settings.jwt_secret_key, algorithms=[_settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise AppError("CDP-AUT-0002") from e
    except JWTError as e:
        raise AppError("CDP-AUT-0003", detail=str(e)) from e