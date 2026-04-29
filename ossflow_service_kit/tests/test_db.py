"""DB layer smoke tests — WAL, FKs, CRUD."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import text

from bjj_service_kit.db import engine as engine_mod
from bjj_service_kit.db import session as session_mod
from bjj_service_kit.db.engine import get_engine, init_db
from bjj_service_kit.db.models import (
    BackgroundJob,
    LibraryChapter,
    LibraryItem,
    Pipeline,
    PipelineStep,
    Setting,
)


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("BJJ_DB_PATH", str(db_path))
    engine_mod.reset_engine()
    session_mod.reset_factory()
    init_db()
    yield db_path
    engine_mod.reset_engine()
    session_mod.reset_factory()


def test_wal_and_fk_pragmas(tmp_db):
    eng = get_engine()
    with eng.connect() as conn:
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
    assert journal.lower() == "wal"
    assert fk == 1


def test_settings_crud(tmp_db):
    from bjj_service_kit.db.session import session_scope

    with session_scope() as s:
        s.add(Setting(key="foo", value='{"a":1}'))
    with session_scope() as s:
        got = s.get(Setting, "foo")
        assert got.value == '{"a":1}'


def test_library_cascade_delete(tmp_db):
    from bjj_service_kit.db.session import session_scope

    with session_scope() as s:
        item = LibraryItem(path="/v/a.mkv", title="A")
        item.chapters.append(LibraryChapter(chapter_path="/v/a_01.mkv", index_num=1))
        s.add(item)
    with session_scope() as s:
        s.delete(s.get(LibraryItem, "/v/a.mkv"))
    with session_scope() as s:
        assert s.get(LibraryChapter, "/v/a_01.mkv") is None


def test_pipeline_with_steps(tmp_db):
    from bjj_service_kit.db.session import session_scope

    with session_scope() as s:
        p = Pipeline(id="pipe1", status="running", input_path="/x.mkv",
                     started_at=datetime.utcnow())
        p.steps.append(PipelineStep(step_name="chapters", status="success"))
        s.add(p)
    with session_scope() as s:
        p = s.get(Pipeline, "pipe1")
        assert len(p.steps) == 1
        assert p.steps[0].step_name == "chapters"


def test_background_job_roundtrip(tmp_db):
    from bjj_service_kit.db.session import session_scope

    with session_scope() as s:
        s.add(BackgroundJob(id="j1", type="scan", status="pending"))
    with session_scope() as s:
        j = s.get(BackgroundJob, "j1")
        assert j.status == "pending"
        j.status = "success"
    with session_scope() as s:
        assert s.get(BackgroundJob, "j1").status == "success"
