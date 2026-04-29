"""Pydantic schemas for the BJJ service kit."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Request body for POST /run."""

    input_path: str = Field(..., description="Absolute path to the instruccional directory or file")
    output_dir: Optional[str] = Field(None, description="Optional output directory override")
    options: dict[str, Any] = Field(default_factory=dict, description="Backend-specific options")


class JobEvent(BaseModel):
    """Event emitted over SSE for a given job."""

    type: Literal["log", "progress", "done", "error"]
    data: Any = None
