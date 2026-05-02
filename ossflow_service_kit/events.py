"""SSE helpers for BJJ service kit."""

from __future__ import annotations

import json
from typing import Iterator

from .runner import JobQueue
from .schemas import JobEvent


def sse_format(event: JobEvent) -> str:
    """Format a JobEvent as SSE ``event: <type>\\ndata: <json>\\n\\n`` frame."""
    payload = json.dumps({"type": event.type, "data": event.data}, default=str)
    return f"event: {event.type}\ndata: {payload}\n\n"


def sse_generator(job_queue: JobQueue) -> Iterator[str]:
    """Yield SSE-formatted frames for each event in the queue until closed.

    Resilience plan (2026-05-02): if the queue is already drained but a
    terminal event is cached, replay it instead of blocking on the empty
    queue. This covers reconnect-after-drain inside the registry's
    retention TTL: the original consumer already pulled SENTINEL so a
    second ``iterator()`` call would hang on ``Queue.get()`` forever.

    Race-free check: we read ``replay_terminal`` AND check ``empty()``
    only after confirming the terminal was already cached. A fresh
    reader for a not-yet-completed job sees ``terminal is None`` → falls
    through to the normal iterator path.
    """
    terminal = job_queue.replay_terminal()
    if terminal is not None and job_queue.is_drained():
        # Fast path: job already completed AND its events already
        # consumed by a prior reader. Replay the verdict and return.
        yield sse_format(terminal)
        return
    for event in job_queue.iterator():
        yield sse_format(event)
