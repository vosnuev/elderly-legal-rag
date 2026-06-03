"""Job models owned by the knowledge runtime boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class JobPhase(StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    STORED = "stored"
    BUILD_STARTED = "build_started"
    DOCUMENT_REGISTERED = "document_registered"
    CHUNKED = "chunked"
    EMBEDDING_DISPATCHED = "embedding_dispatched"
    CANDIDATES_GENERATED = "candidates_generated"
    PENDING_REVIEW = "pending_review"
    REVIEWING = "reviewing"
    NEEDS_RETRY = "needs_retry"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def normalize(cls, value: object) -> "JobPhase":
        raw = getattr(value, "value", value)
        aliases = {
            "staged": cls.RECEIVED.value,
            "uploaded": cls.RECEIVED.value,
            "uploaded_to_database": cls.STORED.value,
            "graph_add_started": cls.BUILD_STARTED.value,
        }
        normalized = aliases.get(str(raw), str(raw))
        try:
            return cls(normalized)
        except ValueError:
            return cls.FAILED


class JobStageStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class JobStage(BaseModel):
    phase: JobPhase
    status: JobStageStatus
    message: str
    path: str | None = None
    error: str | None = None
    recorded_at: datetime = Field(default_factory=utc_now)


class JobRecord(BaseModel):
    job_id: str
    file_name: str
    current_phase: JobPhase
    stages: list[JobStage]
    document_id: str | None = None
    chunk_count: int = 0
    candidate_count: int = 0
    pending_review_count: int = 0
    warning: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def completed(self) -> bool:
        return self.current_phase in {JobPhase.COMPLETED, JobPhase.FAILED}
