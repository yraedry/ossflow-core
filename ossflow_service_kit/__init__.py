"""Shared FastAPI service kit for BJJ backends (chapter-splitter, subtitle-generator, dubbing-generator)."""

from .app_factory import create_app
from .log_bridge import EmitLogHandler, emit_logs, install_emit_handler
from .runner import BaseRunner, JobQueue, JobRegistry
from .schemas import RunRequest, JobEvent

__all__ = [
    "create_app",
    "BaseRunner",
    "JobQueue",
    "JobRegistry",
    "RunRequest",
    "JobEvent",
    "EmitLogHandler",
    "emit_logs",
    "install_emit_handler",
]
