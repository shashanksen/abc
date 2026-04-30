"""SQLAlchemy engine + session factory."""
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


_settings = get_settings()
engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=20,           # per-process — with 2 uvicorn workers = 40 baseline
    max_overflow=10,        # +10 burst per process = 60 max total
    pool_recycle=1800,      # recycle idle connections after 30 min
    pool_timeout=10,        # fail fast if pool exhausted
    future=True,
)

SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


@contextmanager
def get_session() -> Iterator[Session]:
    """Use as context manager outside FastAPI requests."""
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


def db_session() -> Iterator[Session]:
    """FastAPI dependency: yields a session, commits on success, rolls back on error."""
    db = SessionFactory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()