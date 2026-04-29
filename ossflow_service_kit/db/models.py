"""SQLAlchemy ORM models — unified schema for all BJJ services."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-serialized
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class LibraryItem(Base):
    __tablename__ = "library_items"

    path: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String)
    poster_path: Mapped[Optional[str]] = mapped_column(String)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    duration_s: Mapped[Optional[float]] = mapped_column(Float)
    scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    season_dir: Mapped[Optional[str]] = mapped_column(String, index=True)

    chapters: Mapped[list["LibraryChapter"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )


class LibraryChapter(Base):
    __tablename__ = "library_chapters"

    chapter_path: Mapped[str] = mapped_column(String, primary_key=True)
    parent_path: Mapped[Optional[str]] = mapped_column(
        ForeignKey("library_items.path", ondelete="CASCADE"), index=True
    )
    index_num: Mapped[Optional[int]] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String)

    parent: Mapped[Optional[LibraryItem]] = relationship(back_populates="chapters")


class MediaMetadata(Base):
    __tablename__ = "media_metadata"

    video_path: Mapped[str] = mapped_column(String, primary_key=True)
    oracle_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    subs_path: Mapped[Optional[str]] = mapped_column(String)
    dub_path: Mapped[Optional[str]] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    input_path: Mapped[str] = mapped_column(String, nullable=False)
    output_dir: Mapped[Optional[str]] = mapped_column(String)
    options: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    diff: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_s: Mapped[Optional[float]] = mapped_column(Float)

    steps: Mapped[list["PipelineStep"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_pipelines_started", "started_at"),)


class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_s: Mapped[Optional[float]] = mapped_column(Float)
    error: Mapped[Optional[str]] = mapped_column(Text)

    pipeline: Mapped[Pipeline] = relationship(back_populates="steps")


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    result: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


# NOTE: Telegram tables (channels, media, download_jobs) live in the SAME
# SQLite file (bjj.db) but use the native aiosqlite schema owned by the
# telegram-fetcher service (see telegram_fetcher/db.py). They are NOT
# modeled here to avoid schema drift. The unified DB is physical, not
# logical — each service owns its own tables.
