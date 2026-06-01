"""Job observability event models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ObservabilityChannel(StrEnum):
    LIFECYCLE = "lifecycle"
    AGENT_TRANSCRIPT = "agent_transcript"
    WORKER_METRICS = "worker_metrics"
    SERVICE = "service"
    ERROR = "error"


class VisibilityEventType(StrEnum):
    LIFECYCLE = "lifecycle"
    MESSAGE = "message"
    ERROR = "error"
    AGENT = "agent"
    SERVICE = "service"


class ObservabilityEvent(BaseModel):
    job_id: str
    channel: ObservabilityChannel | str
    timestamp: datetime = Field(default_factory=utc_now)
    task_id: str | None = None
    kind: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    event_id: str | None = None

    def with_event_id(self, event_id: str) -> "ObservabilityEvent":
        return self.model_copy(update={"event_id": event_id})
