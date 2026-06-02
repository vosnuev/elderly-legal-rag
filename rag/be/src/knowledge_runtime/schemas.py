"""DTOs exposed from the knowledge runtime boundary to API/FE."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from knowledge_runtime.jobs.models import JobPhase, JobStage
from pipeline.schemas import ReviewAction

SUPPORTED_DOCUMENT_SUFFIXES = {".csv", ".json", ".py", ".txt", ".md"}


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


class DocumentSummary(BaseModel):
    content: str
    source_title: str
    file_name: str
    file_type: str
    location: str | None = None
    url: str | None = None


class DocumentWorkRequest(BaseModel):
    file_name: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_type: str | None = None


class StoredFileWorkRequest(BaseModel):
    job_id: str = Field(min_length=1)
    file_name: str = Field(min_length=1)
    content_type: str | None = None
    file_size: int = Field(ge=0)
    stored_path: Path


class RegisteredDocument(BaseModel):
    document_id: str
    file_name: str
    content_type: str
    content_hash: str


class TaskSnapshot(BaseModel):
    task_id: str
    kind: str
    status: str
    idempotency_key: str
    submitted_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    file_name: str
    current_phase: JobPhase
    completed: bool
    stages: list[JobStage]
    warning: str | None = None
    document_id: str | None = None
    chunk_count: int = 0
    candidate_count: int = 0
    pending_review_count: int = 0
    current_task: TaskSnapshot | None = None


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    note: str | None = None
    reviewer: str = "system"


class RuntimeDependencySummary(BaseModel):
    runtime: str
    settings: str
    database_uri: str
    external_mcp_endpoint: str
    supported_files: list[str]
    worker: dict[str, Any]
