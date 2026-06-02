"""Review decision service."""

from __future__ import annotations

from knowledge_runtime.jobs.projector import JobProjector
from knowledge_runtime.schemas import JobStatusResponse, ReviewDecisionRequest
from knowledge_runtime.tasks.submitter import TaskSubmitter
from query.read.inspection import read_relationship_candidate
from query.read.runtime import list_pending_review_candidates


class ReviewWorkService:
    def __init__(
        self,
        *,
        submitter: TaskSubmitter,
        projector: JobProjector,
    ) -> None:
        self._submitter = submitter
        self._projector = projector

    def list_pending(
        self,
        *,
        limit: int = 50,
        job_id: str | None = None,
        document_id: str | None = None,
    ) -> dict[str, object]:
        return list_pending_review_candidates(
            limit=limit,
            job_id=job_id,
            document_id=document_id,
        )

    async def decide(
        self,
        *,
        candidate_id: str,
        request: ReviewDecisionRequest,
    ) -> JobStatusResponse:
        candidate = read_relationship_candidate(candidate_id)
        candidate_props = _properties(candidate)
        job_id = str(candidate_props.get("job_id") or "")
        if not job_id:
            raise ValueError(f"Candidate has no job_id: {candidate_id}")

        candidate_status = str(candidate_props.get("status") or "pending_review")
        if candidate_status != "pending_review":
            return self._projector.status(job_id)

        await self._submitter.submit_review(
            job_id=job_id,
            candidate_id=candidate_id,
            action=request.action.value,
            reviewer=request.reviewer,
            note=request.note,
        )
        return self._projector.status(job_id)


def _properties(record: dict[str, object]) -> dict[str, object]:
    nested = record.get("properties")
    if isinstance(nested, dict):
        return nested
    return record
