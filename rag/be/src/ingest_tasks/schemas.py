from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    content: str
    source_title: str
    file_name: str
    file_type: str
    location: str | None = None
    url: str | None = None
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class IngestStage(StrEnum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    UPLOADED_TO_DATABASE = "uploaded_to_database"
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


class StageStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class RagIngestRequest(BaseModel):
    job_id: str
    file_name: str
    content_type: str | None = None
    file_size: int
    stored_path: str


class CreateDocumentIngestJobRequest(BaseModel):
    file_name: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_type: str | None = None


class IngestStageResult(BaseModel):
    stage: IngestStage
    status: StageStatus
    message: str
    path: str | None = None
    error: str | None = None


class FileIngestStatusResponse(BaseModel):
    job_id: str
    file_name: str
    current_stage: IngestStage
    completed: bool
    stages: list[IngestStageResult]
    warning: str | None = None
    document_id: str | None = None
    chunk_count: int = 0
    candidate_count: int = 0
    pending_review_count: int = 0


class RagDocument(BaseModel):
    content: str
    source_title: str
    file_name: str
    file_type: str
    location: str | None = None
    url: str | None = None
