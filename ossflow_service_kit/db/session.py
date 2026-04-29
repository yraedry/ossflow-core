"""Session factory + context manager."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy.orm import Session, sessionmaker

from .engine import get_engine

_SessionLocal: Optional[sessionmaker] = None


def _factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _SessionLocal


def get_session() -> Session:
    return _factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Commit on exit, rollback on error, always close."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_factory() -> None:
    global _SessionLocal
    _SessionLocal = None
