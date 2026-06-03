from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class IngestJobPhase(StrEnum):
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
    def normalize(cls, value: object) -> "IngestJobPhase":
        raw = getattr(value, "value", value)
        aliases = {
            "staged": cls.RECEIVED.value,
            "uploaded": cls.RECEIVED.value,
            "uploaded_to_database": cls.STORED.value,
            "graph_add_started": cls.BUILD_STARTED.value,
        }
        return cls(aliases.get(str(raw), str(raw)))


class IngestJobNode(BaseModel):
    """문서 ingest pipeline 실행 상태를 저장하는 operational node.

    `IngestJob`은 FE status 조회와 pipeline progress marker 용도이다. Memgraph에
    저장되지만 semantic knowledge graph의 지식 노드로 취급하지 않는다.
    """

    id: str
    job_id: str
    phase: IngestJobPhase
    document_id: str | None = None
    chunk_count: int = 0
    candidate_count: int = 0
    pending_review_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
