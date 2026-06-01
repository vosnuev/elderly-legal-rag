from __future__ import annotations

from pydantic import BaseModel, Field


class IngestJobNode(BaseModel):
    """문서 ingest pipeline 실행 상태를 저장하는 operational node.

    `IngestJob`은 FE status 조회와 pipeline progress marker 용도이다. Memgraph에
    저장되지만 semantic knowledge graph의 지식 노드로 취급하지 않는다.
    """

    id: str
    job_id: str
    phase: str
    document_id: str | None = None
    chunk_count: int = 0
    candidate_count: int = 0
    pending_review_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
