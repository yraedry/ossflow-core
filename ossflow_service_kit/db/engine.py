"""SQLAlchemy engine factory with SQLite WAL + FK pragmas."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

DEFAULT_DB_PATH = "/data/db/bjj.db"
DEFAULT_BUSY_TIMEOUT_MS = 5000

_engine: Optional[Engine] = None


def _resolve_url(db_path: Optional[str] = None) -> str:
    if db_path is None:
        db_path = os.environ.get("BJJ_DB_PATH", DEFAULT_DB_PATH)
    # Memory sentinel for tests
    if db_path == ":memory:":
        return "sqlite:///:memory:"
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def _apply_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute(f"PRAGMA busy_timeout={DEFAULT_BUSY_TIMEOUT_MS}")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


def get_engine(db_path: Optional[str] = None, *, echo: bool = False) -> Engine:
    """Return singleton engine. Pass db_path explicitly in tests."""
    global _engine
    if _engine is not None and db_path is None:
        return _engine
    url = _resolve_url(db_path)
    engine = create_engine(
        url,
        echo=echo,
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    event.listen(engine, "connect", _apply_pragmas)
    if db_path is None:
        _engine = engine
    return engine


def init_db(db_path: Optional[str] = None) -> Engine:
    """Create all tables (dev/test bootstrap). Production uses Alembic."""
    from .models import Base

    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def reset_engine() -> None:
    """Testing helper — drop cached engine."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
