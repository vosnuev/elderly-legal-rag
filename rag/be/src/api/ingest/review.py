from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query

from knowledge_runtime.schemas import (
    JobStatusResponse,
    ReviewCandidateListResponse,
    ReviewDecisionRequest,
    ReviewJobDecisionRequest,
)
from knowledge_runtime.service import knowledge_runtime

router = APIRouter(tags=["ingest-review"])


@router.get(
    "/api/review/edge-candidates",
    response_model=ReviewCandidateListResponse,
)
def list_edge_candidates(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    job_id: Annotated[str | None, Query(min_length=1)] = None,
    document_id: Annotated[str | None, Query(min_length=1)] = None,
    status: Annotated[Literal["pending", "finished", "all"], Query()] = "pending",
) -> ReviewCandidateListResponse:
    return knowledge_runtime.reviews.list_pending(
        limit=limit,
        job_id=job_id,
        document_id=document_id,
        status_filter=status,
    )


@router.post(
    "/api/review/edge-candidates/{candidate_id}/decision",
    response_model=JobStatusResponse,
)
async def decide_edge_candidate(
    candidate_id: Annotated[str, Path(min_length=1)],
    request: ReviewDecisionRequest,
) -> JobStatusResponse:
    return await knowledge_runtime.reviews.decide(
        candidate_id=candidate_id,
        request=request,
    )


@router.post(
    "/api/review/jobs/{job_id}/decisions",
    response_model=JobStatusResponse,
)
async def decide_edge_candidates_for_job(
    job_id: Annotated[str, Path(min_length=1)],
    request: ReviewJobDecisionRequest,
) -> JobStatusResponse:
    return await knowledge_runtime.reviews.decide_job(
        job_id=job_id,
        request=request,
    )
