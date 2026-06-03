"""DTOs exposed from the knowledge runtime boundary to API/FE."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from knowledge_runtime.jobs.models import JobPhase, JobStage
from pipeline.schemas import ReviewAction

SUPPORTED_DOCUMENT_SUFFIXES = {".csv", ".json", ".py", ".txt", ".md", ".toon"}


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


class RelationshipCandidateSnapshot(BaseModel):
    """FE-facing review queue candidate projection."""

    model_config = ConfigDict(extra="allow")

    id: str = ""
    job_id: str = ""
    left_node: str = ""
    right_node: str = ""
    source_node: str = ""
    target_node: str = ""
    relationship_type: str = ""
    relationship_direction: str = ""
    evidence_node_id: str | None = None
    evidence_text: str = ""
    rationale: str = ""
    source_chunk_id: str = ""
    source_chunk_name: str | None = None
    source_chunk_description: str | None = None
    source_chunk_summary: str | None = None
    source_chunk_text: str | None = None
    source_chunk_index: int | None = None
    source_chunk_label: str | None = None
    target_chunk_id: str | None = None
    target_chunk_name: str | None = None
    target_chunk_description: str | None = None
    target_chunk_summary: str | None = None
    target_chunk_text: str | None = None
    target_chunk_index: int | None = None
    target_chunk_label: str | None = None
    evidence_chunk_name: str | None = None
    evidence_chunk_description: str | None = None
    evidence_chunk_summary: str | None = None
    evidence_chunk_index: int | None = None
    review_note: str | None = None
    review_action: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    status: str = "pending_review"
    version: int = 1
    metadata: dict[str, Any] | str | None = Field(default_factory=dict)


class ReviewCandidateRow(BaseModel):
    candidate: RelationshipCandidateSnapshot


class ReviewCandidateListResponse(BaseModel):
    columns: list[str] = Field(default_factory=lambda: ["candidate"])
    rows: list[ReviewCandidateRow] = Field(default_factory=list)
    row_count: int = 0
    elapsed_ms: float | None = None


class ReviewDecisionRequest(BaseModel):
    action: ReviewAction
    note: str | None = None
    reviewer: str = "system"


class ReviewJobDecision(BaseModel):
    candidate_id: str = Field(min_length=1)
    action: ReviewAction
    note: str | None = None


class ReviewJobDecisionRequest(BaseModel):
    decisions: list[ReviewJobDecision] = Field(min_length=1)
    reviewer: str = "system"


class MemoryDocumentResponse(BaseModel):
    exists: bool = False
    id: str | None = None
    scope: str = "global"
    title: str = "Candidate extraction memory"
    content: str = ""
    version: int = 0
    status: str = "empty"
    author: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] | str | None = Field(default_factory=dict)
    evidence_review_note_ids: list[str] = Field(default_factory=list)
    evidence_candidate_ids: list[str] = Field(default_factory=list)


class MemoryDocumentUpdateRequest(BaseModel):
    content: str = Field(min_length=1)
    title: str = Field(default="Candidate extraction memory", min_length=1)
    update_summary: str = ""
    author: str = "user_memory_settings"


class RuntimeDependencySummary(BaseModel):
    runtime: str
    settings: str
    database_uri: str
    external_mcp_endpoint: str
    supported_files: list[str]
    worker: dict[str, Any]
