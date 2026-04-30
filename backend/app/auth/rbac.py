"""RBAC — guard a route by required module permission."""
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user
from app.common.models import Module, ModuleRole, User, UserModuleAccess
from app.core.database import db_session
from app.core.errors import AppError


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
    """Use as: Depends(require_module_permission("DQ", permission="write"))."""

    def dependency(
        user: Annotated[User, Depends(get_current_user)],
        db:   Annotated[Session, Depends(db_session)],
    ) -> User:
        perms = get_user_permissions_for_module(db, user.id, module_code)
        if not perms:
            raise AppError("CDP-ACC-0031", context={"module": module_code})
        if permission not in perms:
            raise AppError("CDP-ACC-0030",
                           context={"module": module_code, "required": permission})
        return user

    return dependency
