"""Runner abstractions for executing backend jobs in background threads.

Design (SOLID):
- JobQueue: thin wrapper over queue.Queue for SSE event publishing (SRP).
- JobRegistry: maps job_id -> JobQueue (SRP, also DIP for FastAPI deps).
- BaseRunner: orchestrates execution of a user-provided callable in a thread,
  publishing log/progress/done/error events. Depends only on abstractions.
"""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .schemas import JobEvent, RunRequest


SENTINEL = object()


class JobQueue:
    """Thread-safe event queue for a single job.

    Holds a copy of the terminal event (``done`` or ``error``) in
    ``self._terminal`` so reconnects that arrive *after* the iterator
    drained still get the verdict instead of hanging on an empty queue.
    Required for the retention TTL feature (see ``JobRegistry``).
    """

    def __init__(self) -> None:
        self._q: "queue.Queue[Any]" = queue.Queue()
        self._terminal: Optional[JobEvent] = None

    def put(self, event: JobEvent) -> None:
        if event.type in ("done", "error"):
            self._terminal = event
        self._q.put(event)

    def close(self) -> None:
        self._q.put(SENTINEL)

    def iterator(self, timeout: Optional[float] = None):
        """Blocking iterator that yields events until SENTINEL is received."""
        while True:
            item = self._q.get()
            if item is SENTINEL:
                return
            yield item

    def replay_terminal(self) -> Optional[JobEvent]:
        """Return the terminal event if this job already completed.

        Used by the SSE endpoint when a reconnect arrives after the
        original iterator was drained — we yield the cached terminal
        event so the caller sees the verdict instead of blocking on
        an empty queue forever.
        """
        return self._terminal

    def is_drained(self) -> bool:
        """True if the underlying queue has no pending items.

        Used together with ``replay_terminal`` to decide whether a
        reconnect should fast-path replay instead of iterating.
        """
        return self._q.empty()


class JobRegistry:
    """In-memory registry of job queues.

    Completed jobs are kept in the registry for ``retention_seconds``
    after ``drop`` is called (default 120 s). This lets a client
    reconnect within the window and still see the terminal event via
    ``JobQueue.replay_terminal``. After the TTL the job is gone and a
    reconnect gets 404 — at that point the orchestrator must verify the
    filesystem to distinguish "completed and reaped" from "backend died".
    """

    def __init__(self, retention_seconds: float = 120.0) -> None:
        self._jobs: Dict[str, JobQueue] = {}
        self._lock = threading.Lock()
        self._retention_seconds = retention_seconds

    def create(self) -> tuple[str, JobQueue]:
        job_id = str(uuid.uuid4())
        q = JobQueue()
        with self._lock:
            self._jobs[job_id] = q
        return job_id, q

    def get(self, job_id: str) -> Optional[JobQueue]:
        with self._lock:
            return self._jobs.get(job_id)

    def drop(self, job_id: str) -> None:
        """Schedule removal of ``job_id`` after ``retention_seconds``.

        Reconnects within the window still see the queue (with the
        terminal event already buffered via ``JobQueue.replay_terminal``).
        After TTL the job is gone and reconnects get 404.
        """
        def _delayed_drop() -> None:
            with self._lock:
                self._jobs.pop(job_id, None)
        timer = threading.Timer(self._retention_seconds, _delayed_drop)
        timer.daemon = True
        timer.start()


# Callable signature for backend task functions.
# Receives: validated RunRequest, a callback to emit events.
TaskFn = Callable[[RunRequest, Callable[[JobEvent], None]], None]


def validate_input_path(raw: str) -> Path:
    """Validate input_path against path traversal and ensure it is absolute.

    Raises ValueError on rejection.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError("input_path is required")
    # Reject traversal sequences
    if ".." in Path(raw).parts:
        raise ValueError("path traversal not allowed in input_path")
    p = Path(raw)
    if not p.is_absolute():
        raise ValueError("input_path must be absolute")
    return p


@dataclass
class BaseRunner:
    """Executes a TaskFn asynchronously and streams events via JobQueue."""

    task_fn: TaskFn
    registry: JobRegistry = field(default_factory=JobRegistry)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("ossflow_service_kit.runner"))

    def submit(self, request: RunRequest) -> str:
        # Security: validate path up-front. Raises ValueError handled by FastAPI layer.
        validate_input_path(request.input_path)

        job_id, q = self.registry.create()

        def emit(evt: JobEvent) -> None:
            q.put(evt)

        def target() -> None:
            try:
                self.task_fn(request, emit)
                emit(JobEvent(type="done", data={"job_id": job_id}))
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Job %s failed", job_id)
                emit(JobEvent(type="error", data={"message": str(exc)}))
            finally:
                q.close()
                # Schedule retention TTL: clients that reconnect within
                # ``retention_seconds`` still see the terminal event via
                # ``JobQueue.replay_terminal``. After TTL the job entry
                # is removed and reconnects get 404.
                self.registry.drop(job_id)

        t = threading.Thread(target=target, daemon=True, name=f"job-{job_id}")
        t.start()
        return job_id
