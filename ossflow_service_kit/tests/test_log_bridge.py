"""Tests for the logging-to-SSE bridge (log_bridge.py)."""

from __future__ import annotations

import logging

from bjj_service_kit import EmitLogHandler, emit_logs, install_emit_handler
from bjj_service_kit.schemas import JobEvent


def _collector():
    events: list[JobEvent] = []
    return events, events.append


def test_emit_log_handler_forwards_message_and_level():
    events, emit = _collector()
    logger = logging.getLogger("test.bridge.basic")
    logger.setLevel(logging.DEBUG)
    handler = EmitLogHandler(emit, level=logging.INFO)
    logger.addHandler(handler)
    try:
        logger.info("hello")
        logger.warning("careful")
        logger.error("boom")
    finally:
        logger.removeHandler(handler)

    assert [e.type for e in events] == ["log", "log", "log"]
    messages = [e.data["message"] for e in events]
    levels = [e.data["level"] for e in events]
    assert messages == ["hello", "careful", "boom"]
    assert levels == ["INFO", "WARNING", "ERROR"]


def test_emit_log_handler_respects_level_filter():
    events, emit = _collector()
    logger = logging.getLogger("test.bridge.level")
    logger.setLevel(logging.DEBUG)
    handler = EmitLogHandler(emit, level=logging.INFO)
    logger.addHandler(handler)
    try:
        logger.debug("invisible")
        logger.info("visible")
    finally:
        logger.removeHandler(handler)

    assert len(events) == 1
    assert events[0].data["message"] == "visible"


def test_install_emit_handler_attaches_to_root_and_returns_handler():
    events, emit = _collector()
    handler = install_emit_handler(emit, level=logging.INFO)
    try:
        logging.getLogger("any.child").info("root ok")
    finally:
        logging.getLogger().removeHandler(handler)

    assert any(e.data["message"] == "root ok" for e in events)


def test_emit_logs_context_manager_removes_handler_on_exit():
    events, emit = _collector()
    root = logging.getLogger()
    before = list(root.handlers)

    with emit_logs(emit, level=logging.INFO, capture_stdout=False):
        logging.getLogger("test.bridge.ctx").info("inside")
        during = list(root.handlers)

    after = list(root.handlers)

    assert len(during) == len(before) + 1
    assert after == before  # handler detached cleanly
    assert any(e.data["message"] == "inside" for e in events)

    # No duplicate after exit
    events.clear()
    logging.getLogger("test.bridge.ctx").info("outside")
    assert events == []


def test_emit_logs_captures_stdout_prints():
    events, emit = _collector()
    with emit_logs(emit, level=logging.INFO, capture_stdout=True):
        print("pipeline says hi")
        print("  ")  # whitespace ignored
        print("second line")

    messages = [e.data["message"] for e in events if e.type == "log"]
    assert "pipeline says hi" in messages
    assert "second line" in messages
    assert "  " not in messages
