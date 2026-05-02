"""ORM models for the `core` schema."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ENUM, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ─── Users ────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}

    id:             Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                                 server_default=func.uuid_generate_v4())
    email:          Mapped[str]  = mapped_column(String(255), unique=True, nullable=False)
    full_name:      Mapped[str]  = mapped_column(String(255), nullable=False)
    password_hash:  Mapped[str]  = mapped_column(String(255), nullable=False)
    is_active:      Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin:       Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at:     Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ─── Modules ──────────────────────────────────────────────────────────────────
class Module(Base):
    __tablename__ = "modules"
    __table_args__ = {"schema": "core"}

    id:           Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                               server_default=func.uuid_generate_v4())
    code:         Mapped[str]  = mapped_column(String(50), unique=True, nullable=False)
    name:         Mapped[str]  = mapped_column(String(100), nullable=False)
    description:  Mapped[Optional[str]] = mapped_column(Text)
    icon:         Mapped[Optional[str]] = mapped_column(String(50))
    is_enabled:   Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order:   Mapped[int]  = mapped_column(Integer, nullable=False, default=0)
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    features: Mapped[list["ModuleFeature"]] = relationship(back_populates="module")
    roles:    Mapped[list["ModuleRole"]]    = relationship(back_populates="module")


class ModuleFeature(Base):
    __tablename__ = "module_features"
    __table_args__ = (UniqueConstraint("module_id", "code"), {"schema": "core"})

    id:          Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                              server_default=func.uuid_generate_v4())
    module_id:   Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.modules.id"), nullable=False)
    code:        Mapped[str]  = mapped_column(String(100), nullable=False)
    name:        Mapped[str]  = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_enabled:  Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order:  Mapped[int]  = mapped_column(Integer, nullable=False, default=0)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    module: Mapped["Module"] = relationship(back_populates="features")


class ModuleRole(Base):
    __tablename__ = "module_roles"
    __table_args__ = (UniqueConstraint("module_id", "code"), {"schema": "core"})

    id:          Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                              server_default=func.uuid_generate_v4())
    module_id:   Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.modules.id"), nullable=False)
    code:        Mapped[str]  = mapped_column(String(50), nullable=False)
    name:        Mapped[str]  = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    module: Mapped["Module"] = relationship(back_populates="roles")


# ─── Access ───────────────────────────────────────────────────────────────────
class UserModuleAccess(Base):
    __tablename__ = "user_module_access"
    __table_args__ = (UniqueConstraint("user_id", "module_id"), {"schema": "core"})

    id:         Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                             server_default=func.uuid_generate_v4())
    user_id:    Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"), nullable=False)
    module_id:  Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.modules.id"), nullable=False)
    role_id:    Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.module_roles.id"), nullable=False)
    granted_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AccessRequest(Base):
    __tablename__ = "access_requests"
    __table_args__ = {"schema": "core"}

    id:                Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                                    server_default=func.uuid_generate_v4())
    user_id:           Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"), nullable=False)
    module_id:         Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.modules.id"), nullable=False)
    requested_role_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.module_roles.id"), nullable=False)
    justification:     Mapped[Optional[str]] = mapped_column(Text)
    status:            Mapped[str] = mapped_column(
        ENUM("PENDING", "APPROVED", "DENIED", "CANCELLED",
             name="request_status", schema="core", create_type=False),
        nullable=False, default="PENDING"
    )
    decided_by:    Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    decided_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── Audit ────────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "core"}

    id:           Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_id:     Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    actor_email:  Mapped[Optional[str]] = mapped_column(String(255))
    action:       Mapped[str]  = mapped_column(String(100), nullable=False)
    entity_type:  Mapped[str]  = mapped_column(String(50), nullable=False)
    entity_id:    Mapped[Optional[str]] = mapped_column(String(100))
    before_state: Mapped[Optional[dict]] = mapped_column(JSONB)
    after_state:  Mapped[Optional[dict]] = mapped_column(JSONB)
    metadata_:    Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserActivity(Base):
    __tablename__ = "user_activity"
    __table_args__ = {"schema": "core"}

    id:            Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id:       Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"), nullable=False)
    activity_type: Mapped[str]  = mapped_column(String(50), nullable=False)
    module_code:   Mapped[Optional[str]] = mapped_column(String(50))
    feature_code:  Mapped[Optional[str]] = mapped_column(String(100))
    metadata_:     Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    ip_address:    Mapped[Optional[str]] = mapped_column(INET)
    user_agent:    Mapped[Optional[str]] = mapped_column(Text)
    created_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── Feature flags (kill-switch + future flags) ──────────────────────────────
class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = {"schema": "core"}

    code:        Mapped[str]  = mapped_column(String(64), primary_key=True)
    enabled:     Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_by:  Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
