"""ORM models for the DQ (Data Quality) module."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DQDimension(Base):
    __tablename__ = "dimensions"
    __table_args__ = {"schema": "dq"}

    id:           Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                               server_default=func.uuid_generate_v4())
    code:         Mapped[str]  = mapped_column(String(50), unique=True, nullable=False)
    name:         Mapped[str]  = mapped_column(String(100), nullable=False)
    definition:   Mapped[str]  = mapped_column(Text, nullable=False)
    version:      Mapped[int]  = mapped_column(Integer, nullable=False, default=1)
    status:       Mapped[str]  = mapped_column(String(20), nullable=False, default="DRAFT")
    status_changed_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    status_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by:   Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DQBusinessRule(Base):
    __tablename__ = "business_rules"
    __table_args__ = {"schema": "dq"}

    id:           Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                               server_default=func.uuid_generate_v4())
    code:         Mapped[str]  = mapped_column(String(100), unique=True, nullable=False)
    dimension_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dq.dimensions.id"))
    ede_mapping:  Mapped[Optional[str]] = mapped_column(String(255))
    rule_text:    Mapped[str]  = mapped_column(Text, nullable=False)
    version:      Mapped[int]  = mapped_column(Integer, nullable=False, default=1)
    status:       Mapped[str]  = mapped_column(String(20), nullable=False, default="DRAFT")
    created_by:   Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class DQTechnicalRule(Base):
    __tablename__ = "technical_rules"
    __table_args__ = {"schema": "dq"}

    id:           Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True,
                                               server_default=func.uuid_generate_v4())
    code:         Mapped[str]  = mapped_column(String(100), unique=True, nullable=False)
    dimension_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dq.dimensions.id"))
    ede:          Mapped[Optional[str]] = mapped_column(String(255))
    cde:          Mapped[Optional[str]] = mapped_column(String(255))
    attribute:    Mapped[Optional[str]] = mapped_column(String(255))
    rule_expr:    Mapped[str]  = mapped_column(Text, nullable=False)
    status:       Mapped[str]  = mapped_column(String(20), nullable=False, default="DRAFT")
    created_by:   Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("core.users.id"))
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
