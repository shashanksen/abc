"""Admin endpoints — manage users, modules, access requests."""
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.auth import require_admin, get_current_user
from app.common.audit import AuditService
from app.common.models import (
    AccessRequest, Module, ModuleFeature, ModuleRole, User, UserModuleAccess,
)
from app.core.base import BaseRepository, BaseService
from app.core.database import db_session
from app.core.errors import AppError


# ═══════════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════════
class ModuleOut(BaseModel):
    id:          UUID
    code:        str
    name:        str
    description: Optional[str] = None
    icon:        Optional[str] = None
    is_enabled:  bool
    sort_order:  int

    class Config:
        from_attributes = True


class ModuleFeatureOut(BaseModel):
    id:          UUID
    code:        str
    name:        str
    description: Optional[str] = None
    is_enabled:  bool
    sort_order:  int

    class Config:
        from_attributes = True


class ModuleRoleOut(BaseModel):
    id:          UUID
    code:        str
    name:        str
    description: Optional[str] = None
    permissions: list[str]

    class Config:
        from_attributes = True


class ModuleDetailOut(ModuleOut):
    features: list[ModuleFeatureOut]
    roles:    list[ModuleRoleOut]


class AccessRequestCreate(BaseModel):
    module_id:         UUID
    requested_role_id: UUID
    justification:     Optional[str] = Field(None, max_length=2000)


class AccessRequestOut(BaseModel):
    id:                UUID
    user_id:           UUID
    module_id:         UUID
    requested_role_id: UUID
    justification:     Optional[str]
    status:            str
    decided_by:        Optional[UUID]
    decided_at:        Optional[datetime]
    decision_note:     Optional[str]
    created_at:        datetime

    class Config:
        from_attributes = True


class AccessDecision(BaseModel):
    note: Optional[str] = Field(None, max_length=2000)


class GrantAccessRequest(BaseModel):
    user_id:    UUID
    module_id:  UUID
    role_id:    UUID


# ═══════════════════════════════════════════════════════════════════════════════
# Repositories
# ═══════════════════════════════════════════════════════════════════════════════
class ModuleRepository(BaseRepository[Module]):
    model = Module


class AccessRequestRepository(BaseRepository[AccessRequest]):
    model = AccessRequest

    def list_by_status(self, status: str) -> list[AccessRequest]:
        return list(self.db.scalars(
            select(AccessRequest).where(AccessRequest.status == status).order_by(AccessRequest.created_at.desc())
        ))

    def find_pending(self, user_id: UUID, module_id: UUID) -> AccessRequest | None:
        return self.db.scalars(
            select(AccessRequest).where(
                AccessRequest.user_id == user_id,
                AccessRequest.module_id == module_id,
                AccessRequest.status == "PENDING",
            )
        ).first()


class UserModuleAccessRepository(BaseRepository[UserModuleAccess]):
    model = UserModuleAccess


# ═══════════════════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════════════════
class AccessService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.modules  = ModuleRepository(db)
        self.requests = AccessRequestRepository(db)
        self.access   = UserModuleAccessRepository(db)
        self.audit    = AuditService(db)

    # ── User-side: request access ─────────────────────────────────────────────
    def request_access(self, user: User, payload: AccessRequestCreate) -> AccessRequest:
        module = self.modules.get_active(payload.module_id)
        if not module:
            raise AppError("CDP-MOD-0020")
        if not module.is_enabled:
            raise AppError("CDP-MOD-0021")
        if self.requests.find_pending(user.id, module.id):
            raise AppError("CDP-ACC-0034")

        role = self.db.get(ModuleRole, payload.requested_role_id)
        if not role or role.module_id != module.id:
            raise AppError("CDP-ACC-0030", detail="Role does not belong to this module")

        req = AccessRequest(
            user_id=user.id,
            module_id=module.id,
            requested_role_id=role.id,
            justification=payload.justification,
        )
        self.requests.create(req)
        self.audit.record(
            action="ACCESS_REQUESTED",
            entity_type="ACCESS_REQUEST",
            entity_id=req.id,
            actor_id=user.id,
            actor_email=user.email,
            after_state={"module": module.code, "role": role.code},
        )
        return req

    # ── Admin-side: approve / deny ────────────────────────────────────────────
    def decide(self, request_id: UUID, *, admin: User, approve: bool, note: str | None = None) -> AccessRequest:
        req = self.db.get(AccessRequest, request_id)
        if not req:
            raise AppError("CDP-ACC-0032")
        if req.status != "PENDING":
            raise AppError("CDP-ACC-0033", context={"current_status": req.status})

        before = {"status": req.status}
        req.status = "APPROVED" if approve else "DENIED"
        req.decided_by = admin.id
        req.decided_at = datetime.now(timezone.utc)
        req.decision_note = note

        if approve:
            existing = self.db.scalars(
                select(UserModuleAccess).where(
                    UserModuleAccess.user_id == req.user_id,
                    UserModuleAccess.module_id == req.module_id,
                )
            ).first()
            if existing:
                existing.role_id = req.requested_role_id
                existing.granted_by = admin.id
                existing.granted_at = datetime.now(timezone.utc)
                existing.revoked_at = None
            else:
                self.access.create(UserModuleAccess(
                    user_id=req.user_id,
                    module_id=req.module_id,
                    role_id=req.requested_role_id,
                    granted_by=admin.id,
                ))

        self.audit.record(
            action="ACCESS_APPROVED" if approve else "ACCESS_DENIED",
            entity_type="ACCESS_REQUEST",
            entity_id=req.id,
            actor_id=admin.id,
            actor_email=admin.email,
            before_state=before,
            after_state={"status": req.status, "note": note},
        )
        return req

    # ── Admin-side: grant directly without a request ──────────────────────────
    def grant(self, *, admin: User, payload: GrantAccessRequest) -> UserModuleAccess:
        module = self.modules.get_active(payload.module_id)
        if not module:
            raise AppError("CDP-MOD-0020")
        role = self.db.get(ModuleRole, payload.role_id)
        if not role or role.module_id != module.id:
            raise AppError("CDP-ACC-0030", detail="Role does not belong to this module")

        existing = self.db.scalars(
            select(UserModuleAccess).where(
                UserModuleAccess.user_id == payload.user_id,
                UserModuleAccess.module_id == payload.module_id,
            )
        ).first()

        if existing:
            existing.role_id = payload.role_id
            existing.granted_by = admin.id
            existing.granted_at = datetime.now(timezone.utc)
            existing.revoked_at = None
            access = existing
        else:
            access = UserModuleAccess(
                user_id=payload.user_id,
                module_id=payload.module_id,
                role_id=payload.role_id,
                granted_by=admin.id,
            )
            self.access.create(access)

        self.audit.record(
            action="ACCESS_GRANTED",
            entity_type="USER_MODULE_ACCESS",
            entity_id=access.id,
            actor_id=admin.id,
            actor_email=admin.email,
            after_state={
                "user_id": str(payload.user_id),
                "module": module.code,
                "role": role.code,
            },
        )
        return access


# ═══════════════════════════════════════════════════════════════════════════════
# Routers
# ═══════════════════════════════════════════════════════════════════════════════
modules_router = APIRouter(prefix="/api/modules", tags=["modules"])


@modules_router.get("", response_model=list[ModuleOut])
def list_modules(
    db:   Annotated[Session, Depends(db_session)],
    user: Annotated[User, Depends(get_current_user)],
):
    """List modules visible to the current user."""
    if user.is_admin:
        rows = db.scalars(select(Module).where(Module.is_enabled).order_by(Module.sort_order)).all()
        return list(rows)
    rows = db.scalars(
        select(Module)
        .join(UserModuleAccess, UserModuleAccess.module_id == Module.id)
        .where(
            UserModuleAccess.user_id == user.id,
            UserModuleAccess.revoked_at.is_(None),
            Module.is_enabled.is_(True),
        )
        .order_by(Module.sort_order)
    ).all()
    return list(rows)


@modules_router.get("/{module_id}", response_model=ModuleDetailOut)
def get_module(
    module_id: UUID,
    db:        Annotated[Session, Depends(db_session)],
    user:      Annotated[User, Depends(get_current_user)],
):
    module = db.get(Module, module_id)
    if not module:
        raise AppError("CDP-MOD-0020")

    features = db.scalars(
        select(ModuleFeature).where(ModuleFeature.module_id == module.id).order_by(ModuleFeature.sort_order)
    ).all()
    roles = db.scalars(select(ModuleRole).where(ModuleRole.module_id == module.id)).all()

    return ModuleDetailOut(
        **{c.name: getattr(module, c.name) for c in Module.__table__.columns},
        features=[ModuleFeatureOut.model_validate(f) for f in features],
        roles=[ModuleRoleOut.model_validate(r) for r in roles],
    )


# ─── Access requests ──────────────────────────────────────────────────────────
access_router = APIRouter(prefix="/api/access", tags=["access"])


@access_router.post("/request", response_model=AccessRequestOut, status_code=201)
def request_access(
    payload: AccessRequestCreate,
    db:      Annotated[Session, Depends(db_session)],
    user:    Annotated[User, Depends(get_current_user)],
):
    return AccessService(db).request_access(user, payload)


@access_router.get("/my-requests", response_model=list[AccessRequestOut])
def my_requests(
    db:   Annotated[Session, Depends(db_session)],
    user: Annotated[User, Depends(get_current_user)],
):
    rows = db.scalars(
        select(AccessRequest).where(AccessRequest.user_id == user.id).order_by(AccessRequest.created_at.desc())
    ).all()
    return list(rows)


# ─── Admin endpoints ──────────────────────────────────────────────────────────
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.get("/access-requests", response_model=list[AccessRequestOut])
def list_requests(
    db:     Annotated[Session, Depends(db_session)],
    _admin: Annotated[User, Depends(require_admin)],
    status: str = Query("PENDING"),
):
    return AccessRequestRepository(db).list_by_status(status)


@admin_router.post("/access-requests/{request_id}/approve", response_model=AccessRequestOut)
def approve_request(
    request_id: UUID,
    body:       AccessDecision,
    db:         Annotated[Session, Depends(db_session)],
    admin:      Annotated[User, Depends(require_admin)],
):
    return AccessService(db).decide(request_id, admin=admin, approve=True, note=body.note)


@admin_router.post("/access-requests/{request_id}/deny", response_model=AccessRequestOut)
def deny_request(
    request_id: UUID,
    body:       AccessDecision,
    db:         Annotated[Session, Depends(db_session)],
    admin:      Annotated[User, Depends(require_admin)],
):
    return AccessService(db).decide(request_id, admin=admin, approve=False, note=body.note)


@admin_router.post("/access/grant", status_code=201)
def grant_access(
    payload: GrantAccessRequest,
    db:      Annotated[Session, Depends(db_session)],
    admin:   Annotated[User, Depends(require_admin)],
):
    AccessService(db).grant(admin=admin, payload=payload)
    return {"granted": True}


@admin_router.get("/users", response_model=list[dict])
def list_users(
    db:     Annotated[Session, Depends(db_session)],
    _admin: Annotated[User, Depends(require_admin)],
):
    rows = db.scalars(
        select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc())
    ).all()
    return [
        {"id": str(u.id), "email": u.email, "full_name": u.full_name,
         "is_admin": u.is_admin, "is_active": u.is_active,
         "last_login_at": u.last_login_at}
        for u in rows
    ]
