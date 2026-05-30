from __future__ import annotations

from enum import StrEnum
from typing import Any

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


class RegisteredDocument(BaseModel):
    id: str
    entry_number: int
    document_version: int = 1
    content_hash: str
    raw_content: str
    file_name: str
    source_type: str
    source_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    reason: str = ""
    start_unique_string: str
    end_unique_string: str
    start_char: int | None = None
    end_char: int | None = None
    embedding_status: str = "pending"
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationshipCandidate(BaseModel):
    id: str
    job_id: str
    source_node: str
    target_node: str
    relationship_type: str
    source_chunk_id: str
    evidence_text: str
    rationale: str
    status: str = "pending_review"
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackJudgeResult(BaseModel):
    ready_for_review: bool
    incomplete: bool = False
    reason: str = ""


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    note: str | None = None
    reviewer: str = "system"


class IngestGraphResult(BaseModel):
    job_id: str
    phase: GraphIngestPhase
    document_id: str | None = None
    chunk_count: int = 0
    candidate_count: int = 0
    pending_review_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
