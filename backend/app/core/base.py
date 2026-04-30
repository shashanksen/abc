"""
OOP base classes used by every module.

  BaseRepository  : SQL access layer. One per ORM model.
  BaseService     : Business logic layer. Composes repositories + audit + auth.

Both are generic and reusable. Every new module follows the same pattern.
"""
from datetime import datetime, timezone
from typing import Any, Generic, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError


T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic CRUD repository tied to a specific ORM model.

    Subclasses set:
      model = MyOrmModel

    Soft-delete-aware: queries automatically filter `deleted_at IS NULL`
    when the model has that column.
    """
    model: Type[T]

    def __init__(self, db: Session):
        self.db = db

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _supports_soft_delete(self) -> bool:
        return hasattr(self.model, "deleted_at")

    def _base_query(self):
        stmt = select(self.model)
        if self._supports_soft_delete():
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    # ── Read ─────────────────────────────────────────────────────────────────
    def get(self, id_: UUID | str) -> Optional[T]:
        return self.db.get(self.model, id_)

    def get_active(self, id_: UUID | str) -> Optional[T]:
        row = self.get(id_)
        if row is None:
            return None
        if self._supports_soft_delete() and getattr(row, "deleted_at", None) is not None:
            return None
        return row

    def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:
        stmt = self._base_query().limit(limit).offset(offset)
        return list(self.db.scalars(stmt))

    def find_by(self, **kwargs) -> Optional[T]:
        stmt = self._base_query()
        for k, v in kwargs.items():
            stmt = stmt.where(getattr(self.model, k) == v)
        return self.db.scalars(stmt).first()

    # ── Write ────────────────────────────────────────────────────────────────
    def create(self, obj: T) -> T:
        self.db.add(obj)
        self.db.flush()  # populate PK without committing
        return obj

    def update(self, obj: T, **fields) -> T:
        for k, v in fields.items():
            setattr(obj, k, v)
        self.db.flush()
        return obj

    def soft_delete(self, obj: T) -> None:
        if not self._supports_soft_delete():
            raise AppError("CDP-SYS-0091", detail=f"{self.model.__name__} does not support soft delete")
        setattr(obj, "deleted_at", datetime.now(timezone.utc))
        self.db.flush()

    def hard_delete(self, obj: T) -> None:
        self.db.delete(obj)
        self.db.flush()


class BaseService:
    """Base for service classes. Subclasses inject any repos they need.

    Convention: services raise AppError with registered codes; HTTP layer
    converts those to responses.
    """
    def __init__(self, db: Session):
        self.db = db
