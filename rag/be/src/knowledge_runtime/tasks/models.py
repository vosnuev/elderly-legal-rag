"""Task models for background build and review executions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from knowledge_runtime.jobs.models import utc_now


class TaskKind(StrEnum):
    BUILD = "build"
    REVIEW = "review"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskRecord(BaseModel):
    task_id: str
    idempotency_key: str
    job_id: str
    kind: TaskKind
    status: TaskStatus = TaskStatus.QUEUED
    payload: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class TaskSubmission(BaseModel):
    task: TaskRecord
    accepted: bool
