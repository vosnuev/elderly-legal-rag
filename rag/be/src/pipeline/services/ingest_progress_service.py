from __future__ import annotations

from pipeline.schemas import GraphIngestPhase, IngestGraphResult
from observability.logger import bind_logger
from query.write import upsert_ingest_job_progress


class IngestProgressService:
    def __init__(self) -> None:
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
        upsert_ingest_job_progress(
            job_id=job_id,
            phase=phase.value,
            document_id=document_id,
            chunk_count=chunk_count,
            candidate_count=candidate_count,
            pending_review_count=pending_review_count,
            warnings=warnings or [],
            errors=errors or [],
        )
        self._logger.bind(
            job_id=job_id,
            phase=phase.value,
            document_id=document_id,
            chunk_count=chunk_count,
            candidate_count=candidate_count,
            error_count=len(errors or []),
        ).info("ingest progress marked")
        return result
