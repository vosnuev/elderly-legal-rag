from __future__ import annotations

from agents.graph_ingest.schemas import GraphIngestPhase, IngestGraphResult
from logger import bind_logger
from query.service import MemgraphQueryService, get_memgraph_query_service


class IngestProgressService:
    def __init__(self, query_service: MemgraphQueryService | None = None) -> None:
        self._query_service = query_service or get_memgraph_query_service()
        self._logger = bind_logger(component="ingest_progress_service")

    def mark(
        self,
        *,
        job_id: str,
        phase: GraphIngestPhase,
        document_id: str | None,
        chunk_count: int,
        candidate_count: int,
        warnings: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> IngestGraphResult:
        pending_review_count = candidate_count if phase is GraphIngestPhase.PENDING_REVIEW else 0
        result = IngestGraphResult(
            job_id=job_id,
            phase=phase,
            document_id=document_id,
            chunk_count=chunk_count,
            candidate_count=candidate_count,
            pending_review_count=pending_review_count,
            warnings=warnings or [],
            errors=errors or [],
        )
        self._query_service.store_ingest_progress(result.model_dump())
        self._logger.bind(
            job_id=job_id,
            phase=phase.value,
            document_id=document_id,
            chunk_count=chunk_count,
            candidate_count=candidate_count,
            error_count=len(errors or []),
        ).info("ingest progress marked")
        return result
