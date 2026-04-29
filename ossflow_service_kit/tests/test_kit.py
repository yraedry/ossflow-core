"""Tests for bjj_service_kit: factory, runner, events, security."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from bjj_service_kit import BaseRunner, JobEvent, RunRequest, create_app
from bjj_service_kit.runner import validate_input_path


# --- validate_input_path --------------------------------------------------


def test_validate_input_path_accepts_absolute_path(tmp_path):
    result = validate_input_path(str(tmp_path))
    assert result.is_absolute()


def test_validate_input_path_rejects_traversal():
    with pytest.raises(ValueError):
        validate_input_path("C:/proyectos/../etc/passwd")


def test_validate_input_path_rejects_relative():
    with pytest.raises(ValueError):
        validate_input_path("relative/path")


def test_validate_input_path_rejects_empty():
    with pytest.raises(ValueError):
        validate_input_path("")


# --- App factory / endpoints ----------------------------------------------


def _noop_task(req: RunRequest, emit):
    emit(JobEvent(type="log", data={"message": "started"}))
    emit(JobEvent(type="progress", data={"pct": 50}))


def _make_client(task=_noop_task, service_name="test-service"):
    app = create_app(service_name=service_name, task_fn=task)
    return TestClient(app)


def test_health_returns_ok():
    client = _make_client(service_name="kit-test")
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "kit-test"}


def test_run_returns_job_id(tmp_path):
    client = _make_client()
    r = client.post("/run", json={"input_path": str(tmp_path)})
    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body and len(body["job_id"]) > 0


def test_run_rejects_path_traversal():
    client = _make_client()
    r = client.post("/run", json={"input_path": "C:/proyectos/../secret"})
    assert r.status_code == 400


def test_run_rejects_relative_path():
    client = _make_client()
    r = client.post("/run", json={"input_path": "relative"})
    assert r.status_code == 400


def test_events_streams_done(tmp_path):
    client = _make_client()
    r = client.post("/run", json={"input_path": str(tmp_path)})
    job_id = r.json()["job_id"]

    with client.stream("GET", f"/events/{job_id}") as resp:
        assert resp.status_code == 200
        text = "".join(resp.iter_text())

    assert "event: log" in text
    assert "event: progress" in text
    assert "event: done" in text


def test_events_streams_error_on_task_failure(tmp_path):
    def failing_task(req, emit):
        raise RuntimeError("boom")

    client = _make_client(task=failing_task)
    r = client.post("/run", json={"input_path": str(tmp_path)})
    job_id = r.json()["job_id"]

    with client.stream("GET", f"/events/{job_id}") as resp:
        text = "".join(resp.iter_text())

    assert "event: error" in text
    assert "boom" in text


def test_events_404_on_unknown_job():
    client = _make_client()
    r = client.get("/events/does-not-exist")
    assert r.status_code == 404
