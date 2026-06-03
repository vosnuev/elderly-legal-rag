"""Review decision service."""

from __future__ import annotations

from typing import Literal

from knowledge_runtime.jobs.projector import JobProjector
from knowledge_runtime.schemas import (
    JobStatusResponse,
    ReviewCandidateListResponse,
    ReviewDecisionRequest,
    ReviewJobDecisionRequest,
)
from knowledge_runtime.tasks.submitter import TaskSubmitter
from query.read.inspection import read_relationship_candidate
from query.read.runtime import list_pending_review_candidates

ReviewCandidateStatusFilter = Literal["pending", "finished", "all"]


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
        status_filter: ReviewCandidateStatusFilter = "pending",
    ) -> ReviewCandidateListResponse:
        return ReviewCandidateListResponse.model_validate(
            list_pending_review_candidates(
                limit=limit,
                job_id=job_id,
                document_id=document_id,
                status_filter=status_filter,
            )
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

    async def decide_job(
        self,
        *,
        job_id: str,
        request: ReviewJobDecisionRequest,
    ) -> JobStatusResponse:
        decisions: list[dict[str, object]] = []
        for decision in request.decisions:
            candidate = read_relationship_candidate(decision.candidate_id)
            candidate_props = _properties(candidate)
            candidate_job_id = str(candidate_props.get("job_id") or "")
            if candidate_job_id != job_id:
                raise ValueError(
                    f"Candidate {decision.candidate_id} does not belong to job {job_id}."
                )
            if str(candidate_props.get("status") or "pending_review") != "pending_review":
                continue
            decisions.append(
                {
                    "candidate_id": decision.candidate_id,
                    "action": decision.action.value,
                    "note": decision.note,
                }
            )

        if decisions:
            await self._submitter.submit_review_batch(
                job_id=job_id,
                reviewer=request.reviewer,
                decisions=decisions,
            )
        return self._projector.status(job_id)


def _properties(record: dict[str, object]) -> dict[str, object]:
    nested = record.get("properties")
    if isinstance(nested, dict):
        return nested
    return record
