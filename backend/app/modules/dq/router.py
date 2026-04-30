"""DQ (Data Quality) module — example reusable module."""
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user
from app.auth.rbac import require_module_permission
from app.common.audit import AuditService
from app.common.models import User
from app.core.base import BaseRepository, BaseService
from app.core.database import db_session
from app.core.errors import AppError
from app.modules.dq.models import DQDimension, DQBusinessRule, DQTechnicalRule


MODULE_CODE = "DQ"  # used by RBAC


# ═══════════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════════
class DimensionCreate(BaseModel):
    code:       str = Field(min_length=1, max_length=50)
    name:       str = Field(min_length=1, max_length=100)
    definition: str = Field(min_length=1)


class DimensionUpdate(BaseModel):
    name:       Optional[str] = Field(None, min_length=1, max_length=100)
    definition: Optional[str] = None
    status:     Optional[str] = Field(None, pattern="^(DRAFT|ACTIVE|RETIRED)$")


class DimensionOut(BaseModel):
    id:         UUID
    code:       str
    name:       str
    definition: str
    version:    int
    status:     str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BusinessRuleCreate(BaseModel):
    code:         str = Field(min_length=1, max_length=100)
    dimension_id: Optional[UUID] = None
    ede_mapping:  Optional[str] = Field(None, max_length=255)
    rule_text:    str = Field(min_length=1)


class BusinessRuleOut(BaseModel):
    id:           UUID
    code:         str
    dimension_id: Optional[UUID]
    ede_mapping:  Optional[str]
    rule_text:    str
    version:      int
    status:       str
    created_at:   datetime
    updated_at:   datetime

    class Config:
        from_attributes = True


class TechnicalRuleCreate(BaseModel):
    code:         str = Field(min_length=1, max_length=100)
    dimension_id: Optional[UUID] = None
    ede:          Optional[str] = Field(None, max_length=255)
    cde:          Optional[str] = Field(None, max_length=255)
    attribute:    Optional[str] = Field(None, max_length=255)
    rule_expr:    str = Field(min_length=1)


class TechnicalRuleOut(BaseModel):
    id:           UUID
    code:         str
    dimension_id: Optional[UUID]
    ede:          Optional[str]
    cde:          Optional[str]
    attribute:    Optional[str]
    rule_expr:    str
    status:       str
    created_at:   datetime
    updated_at:   datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════════
# Repositories
# ═══════════════════════════════════════════════════════════════════════════════
class DimensionRepository(BaseRepository[DQDimension]):
    model = DQDimension

    def get_by_code(self, code: str) -> DQDimension | None:
        return self.find_by(code=code.upper())


class BusinessRuleRepository(BaseRepository[DQBusinessRule]):
    model = DQBusinessRule


class TechnicalRuleRepository(BaseRepository[DQTechnicalRule]):
    model = DQTechnicalRule


# ═══════════════════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════════════════
class DQService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        self.dims     = DimensionRepository(db)
        self.business = BusinessRuleRepository(db)
        self.technical = TechnicalRuleRepository(db)
        self.audit    = AuditService(db)

    # ── Dimensions ────────────────────────────────────────────────────────────
    def create_dimension(self, *, user: User, data: DimensionCreate) -> DQDimension:
        if self.dims.get_by_code(data.code):
            raise AppError("CDP-DQD-0041", context={"code": data.code})

        dim = DQDimension(
            code=data.code.upper(),
            name=data.name.strip(),
            definition=data.definition,
            created_by=user.id,
        )
        self.dims.create(dim)
        self.audit.record(
            action="DQ_DIMENSION_CREATED",
            entity_type="DQ_DIMENSION",
            entity_id=dim.id,
            actor_id=user.id, actor_email=user.email,
            after_state={"code": dim.code, "name": dim.name},
        )
        return dim

    def update_dimension(self, *, user: User, dim_id: UUID, data: DimensionUpdate) -> DQDimension:
        dim = self.dims.get_active(dim_id)
        if not dim:
            raise AppError("CDP-DQD-0040")

        before = {"name": dim.name, "definition": dim.definition, "status": dim.status}
        if data.name is not None:
            dim.name = data.name.strip()
        if data.definition is not None:
            dim.definition = data.definition
        if data.status is not None and data.status != dim.status:
            dim.status = data.status
            dim.status_changed_by = user.id
            dim.status_changed_at = datetime.utcnow()
        dim.version += 1
        self.db.flush()

        self.audit.record(
            action="DQ_DIMENSION_UPDATED",
            entity_type="DQ_DIMENSION",
            entity_id=dim.id,
            actor_id=user.id, actor_email=user.email,
            before_state=before,
            after_state={"name": dim.name, "definition": dim.definition, "status": dim.status},
        )
        return dim

    def list_dimensions(self) -> list[DQDimension]:
        return list(self.db.scalars(
            select(DQDimension).where(DQDimension.deleted_at.is_(None)).order_by(DQDimension.code)
        ))

    # ── Business rules ────────────────────────────────────────────────────────
    def create_business_rule(self, *, user: User, data: BusinessRuleCreate) -> DQBusinessRule:
        if self.business.find_by(code=data.code):
            raise AppError("CDP-DQR-0051", context={"code": data.code})
        rule = DQBusinessRule(
            code=data.code,
            dimension_id=data.dimension_id,
            ede_mapping=data.ede_mapping,
            rule_text=data.rule_text,
            created_by=user.id,
        )
        self.business.create(rule)
        self.audit.record(
            action="DQ_BUSINESS_RULE_CREATED",
            entity_type="DQ_BUSINESS_RULE",
            entity_id=rule.id,
            actor_id=user.id, actor_email=user.email,
            after_state={"code": rule.code},
        )
        return rule

    # ── Technical rules ───────────────────────────────────────────────────────
    def create_technical_rule(self, *, user: User, data: TechnicalRuleCreate) -> DQTechnicalRule:
        if self.technical.find_by(code=data.code):
            raise AppError("CDP-DQR-0051", context={"code": data.code})
        rule = DQTechnicalRule(
            code=data.code,
            dimension_id=data.dimension_id,
            ede=data.ede, cde=data.cde, attribute=data.attribute,
            rule_expr=data.rule_expr,
            created_by=user.id,
        )
        self.technical.create(rule)
        self.audit.record(
            action="DQ_TECHNICAL_RULE_CREATED",
            entity_type="DQ_TECHNICAL_RULE",
            entity_id=rule.id,
            actor_id=user.id, actor_email=user.email,
            after_state={"code": rule.code},
        )
        return rule


# ═══════════════════════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════════════════════
router = APIRouter(prefix="/api/dq", tags=["dq"])

read_required  = require_module_permission(MODULE_CODE, permission="read")
write_required = require_module_permission(MODULE_CODE, permission="write")


# ─── Dimensions ───────────────────────────────────────────────────────────────
@router.get("/dimensions", response_model=list[DimensionOut])
def list_dimensions(
    db:    Annotated[Session, Depends(db_session)],
    _user: Annotated[User, Depends(read_required)],
):
    return DQService(db).list_dimensions()


@router.post("/dimensions", response_model=DimensionOut, status_code=201)
def create_dimension(
    data: DimensionCreate,
    db:   Annotated[Session, Depends(db_session)],
    user: Annotated[User, Depends(write_required)],
):
    return DQService(db).create_dimension(user=user, data=data)


@router.patch("/dimensions/{dim_id}", response_model=DimensionOut)
def update_dimension(
    dim_id: UUID,
    data:   DimensionUpdate,
    db:     Annotated[Session, Depends(db_session)],
    user:   Annotated[User, Depends(write_required)],
):
    return DQService(db).update_dimension(user=user, dim_id=dim_id, data=data)


# ─── Business rules ───────────────────────────────────────────────────────────
@router.get("/business-rules", response_model=list[BusinessRuleOut])
def list_business_rules(
    db:    Annotated[Session, Depends(db_session)],
    _user: Annotated[User, Depends(read_required)],
):
    return list(db.scalars(select(DQBusinessRule).where(DQBusinessRule.deleted_at.is_(None))))


@router.post("/business-rules", response_model=BusinessRuleOut, status_code=201)
def create_business_rule(
    data: BusinessRuleCreate,
    db:   Annotated[Session, Depends(db_session)],
    user: Annotated[User, Depends(write_required)],
):
    return DQService(db).create_business_rule(user=user, data=data)


# ─── Technical rules ──────────────────────────────────────────────────────────
@router.get("/technical-rules", response_model=list[TechnicalRuleOut])
def list_technical_rules(
    db:    Annotated[Session, Depends(db_session)],
    _user: Annotated[User, Depends(read_required)],
):
    return list(db.scalars(select(DQTechnicalRule).where(DQTechnicalRule.deleted_at.is_(None))))


@router.post("/technical-rules", response_model=TechnicalRuleOut, status_code=201)
def create_technical_rule(
    data: TechnicalRuleCreate,
    db:   Annotated[Session, Depends(db_session)],
    user: Annotated[User, Depends(write_required)],
):
    return DQService(db).create_technical_rule(user=user, data=data)
