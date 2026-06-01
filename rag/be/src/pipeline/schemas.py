from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GraphIngestPhase(StrEnum):
    STAGED = "staged"
    GRAPH_ADD_STARTED = "graph_add_started"
    DOCUMENT_REGISTERED = "document_registered"
    CHUNKED = "chunked"
    CHUNKS_STORED = "chunks_stored"
    EMBEDDING_DISPATCHED = "embedding_dispatched"
    CANDIDATES_GENERATED = "candidates_generated"
    PENDING_REVIEW = "pending_review"
    NEEDS_RETRY = "needs_retry"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewAction(StrEnum):
    YES = "yes"
    NO = "no"
    RETRY = "retry"


class FeedbackJudgeResult(BaseModel):
    ready_for_review: bool
    incomplete: bool = False
    reason: str = ""


class IngestGraphResult(BaseModel):
    job_id: str
    phase: GraphIngestPhase
    document_id: str | None = None
    chunk_count: int = 0
    candidate_count: int = 0
    pending_review_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
