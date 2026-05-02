"""RBAC — guard a route by required module permission.

Accepts two token types:
  - type=access            standard user session — checks DB for user's
                           role and permissions on the requested module.
  - type=agent_callback    short-lived on-behalf-of token from the agent —
                           checks the `scope` claim matches the required
                           (module, permission). DB role lookup is skipped
                           because the scope itself is the authorization.

Either way, the User object returned is the user who initiated the action.
"""
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.models import Module, ModuleRole, User, UserModuleAccess
from app.core.database import db_session
from app.core.errors import AppError
from app.core.security import decode_token


_bearer = HTTPBearer(auto_error=False)


def _decode_or_raise(creds: HTTPAuthorizationCredentials | None) -> dict:
    if creds is None:
        raise AppError("CDP-AUT-0006")
    return decode_token(creds.credentials)


def _resolve_user(claims: dict, db: Session) -> User:
    token_type = claims.get("type")
    if token_type not in ("access", "agent_callback"):
        raise AppError("CDP-AUT-0007", context={"type": token_type})

    try:
        user_id = UUID(claims["sub"])
    except (KeyError, ValueError) as e:
        raise AppError("CDP-AUT-0003", detail=str(e)) from e

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("CDP-AUT-0004")
    return user


def get_user_permissions_for_module(
    db: Session, user_id: UUID, module_code: str
) -> set[str]:
    """Return the set of permission strings the user has on the given module.

    Admins implicitly get all permissions.
    """
    user = db.get(User, user_id)
    if not user:
        return set()
    if user.is_admin:
        return {"read", "write", "delete", "manage"}

    stmt = (
        select(ModuleRole.permissions)
        .join(UserModuleAccess, UserModuleAccess.role_id == ModuleRole.id)
        .join(Module, Module.id == ModuleRole.module_id)
        .where(
            UserModuleAccess.user_id == user_id,
            UserModuleAccess.revoked_at.is_(None),
            Module.code == module_code.upper(),
            Module.is_enabled.is_(True),
        )
    )
    perms = db.scalar(stmt)
    return set(perms or [])


def require_module_permission(module_code: str, *, permission: str = "read") -> Callable:
    """Depends() factory — gate a route by module + permission.

    Use as: Depends(require_module_permission("DQ", permission="write"))
    """

    def dependency(
        creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        db:    Annotated[Session, Depends(db_session)],
    ) -> User:
        claims = _decode_or_raise(creds)
        user = _resolve_user(claims, db)

        # Agent callback path: scope claim drives the check, no DB role lookup.
        if claims.get("type") == "agent_callback":
            expected_scope = f"{module_code.upper()}:{permission}"
            if claims.get("scope") != expected_scope:
                raise AppError(
                    "CDP-AUT-0008",
                    context={"expected": expected_scope, "actual": claims.get("scope")},
                )
            return user

        # Regular access token path.
        perms = get_user_permissions_for_module(db, user.id, module_code)
        if not perms:
            raise AppError("CDP-ACC-0031", context={"module": module_code})
        if permission not in perms:
            raise AppError("CDP-ACC-0030",
                           context={"module": module_code, "required": permission})
        return user

    return dependency
