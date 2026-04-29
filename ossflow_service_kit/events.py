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
    """Yield SSE-formatted frames for each event in the queue until closed."""
    for event in job_queue.iterator():
        yield sse_format(event)
