"""Bridge from Python logging / stdout to JobEvent emit callback.

Responsibility (SRP): translate logging records (and optionally stdout writes)
into ``JobEvent(type="log", ...)`` instances pushed to the SSE emitter.

Used by the FastAPI wrappers of chapter-splitter, subtitle-generator and
dubbing-generator so the real pipeline output reaches the frontend's log panel.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Callable, Iterator, Optional

from .schemas import JobEvent


EmitFn = Callable[[JobEvent], None]


class EmitLogHandler(logging.Handler):
    """Logging handler that forwards records as ``JobEvent`` log events."""

    def __init__(self, emit: EmitFn, level: int = logging.INFO) -> None:
        super().__init__(level=level)
        self._emit = emit
        # Minimal format; the UI adds its own timestamp/decoration.
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            message = self.format(record)
            self._emit(
                JobEvent(
                    type="log",
                    data={"message": message, "level": record.levelname},
                )
            )
        except Exception:  # noqa: BLE001 - never let logging crash the job
            self.handleError(record)


def install_emit_handler(
    emit: EmitFn,
    level: int = logging.INFO,
    root: Optional[logging.Logger] = None,
) -> EmitLogHandler:
    """Attach an ``EmitLogHandler`` to ``root`` (default: root logger).

    Returns the handler so the caller can remove it later.
    """
    target = root if root is not None else logging.getLogger()
    handler = EmitLogHandler(emit, level=level)
    # Ensure the logger itself lets records through at this level.
    if target.level == logging.NOTSET or target.level > level:
        target.setLevel(level)
    target.addHandler(handler)
    return handler


class _StreamToEmit:
    """File-like object that forwards non-empty writes as log JobEvents.

    Used with ``contextlib.redirect_stdout`` to capture ``print`` calls made by
    pipelines that bypass the ``logging`` module.
    """

    def __init__(self, emit: EmitFn, level: str = "INFO") -> None:
        self._emit = emit
        self._level = level
        self._buffer = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buffer += s
        # Emit complete lines only; buffer the tail.
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            if line.strip():
                self._emit(
                    JobEvent(type="log", data={"message": line, "level": self._level})
                )
        return len(s)

    def flush(self) -> None:
        if self._buffer.strip():
            self._emit(
                JobEvent(
                    type="log",
                    data={"message": self._buffer.strip(), "level": self._level},
                )
            )
        self._buffer = ""

    # Some callers probe for these.
    def isatty(self) -> bool:
        return False


@contextlib.contextmanager
def emit_logs(
    emit: EmitFn,
    level: int = logging.INFO,
    *,
    capture_stdout: bool = True,
    root: Optional[logging.Logger] = None,
) -> Iterator[EmitLogHandler]:
    """Context manager: install logging bridge (and optionally stdout capture).

    On exit the handler is detached so subsequent jobs don't receive duplicate
    events and stdout is restored.
    """
    target = root if root is not None else logging.getLogger()
    handler = install_emit_handler(emit, level=level, root=target)
    stdout_cm: contextlib.AbstractContextManager
    if capture_stdout:
        stdout_cm = contextlib.redirect_stdout(_StreamToEmit(emit))
    else:
        stdout_cm = contextlib.nullcontext()
    try:
        with stdout_cm:
            yield handler
    finally:
        target.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001
            pass
